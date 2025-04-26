import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import datetime
import re
import logging
import gzip
import yaml
import validators
from urllib.robotparser import RobotFileParser
from aiolimiter import AsyncLimiter
from pathlib import Path

# Configuration
CONFIG = {
    'max_urls_per_sitemap': 50000,
    'max_concurrent_requests': 10,
    'requests_per_second': 2,
    'max_depth': 3,
    'exclude_patterns': ['login', 'admin', 'wp-admin', 'logout'],
    'valid_extensions': ['.html', '.php', '.asp', '.aspx', '']
}

def setup_logging(output_dir):
    log_file = output_dir / 'sitemap_generator.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def load_config():
    config_path = Path('sitemap_config.yaml')
    if config_path.exists():
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f) or {}
        CONFIG.update(user_config)
    return CONFIG

def validate_url(url):
    if not validators.url(url):
        raise ValueError("Invalid URL format. Please include protocol (http:// or https://)")
    return url.rstrip('/')

async def check_robots_txt(url, session):
    logger = logging.getLogger(__name__)
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        async with session.get(robots_url, timeout=5) as response:
            if response.status == 200:
                text = await response.text()
                rp.parse(text.splitlines())
                logger.info(f"Successfully parsed robots.txt from {robots_url}")
                return rp
            else:
                logger.warning(f"Failed to fetch robots.txt from {robots_url}: Status {response.status}")
                return None
    except Exception as e:
        logger.warning(f"Could not read robots.txt from {robots_url}: {e}")
        return None

def clean_url(url, base_url):
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if urlparse(base_url).netloc != urlparse(clean).netloc:
        return None
    return clean

async def crawl_url(url, depth, session, robots_parser, visited, config, limiter):
    if url in visited or depth > config['max_depth']:
        return set()
    
    visited.add(url)
    
    if robots_parser and not robots_parser.can_fetch("*", url):
        logging.info(f"Skipping {url} - disallowed by robots.txt")
        return set()
    
    new_urls = set()
    
    async with limiter:
        try:
            async with session.get(url, headers={'User-Agent': 'SitemapGenerator/2.0'}) as response:
                if response.status != 200 or 'text/html' not in response.headers.get('content-type', ''):
                    return set()
                
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                
                # Check for canonical URL
                canonical = soup.find('link', rel='canonical')
                if canonical and canonical.get('href'):
                    canonical_url = clean_url(canonical['href'], url)
                    if canonical_url and canonical_url != url:
                        visited.add(canonical_url)
                        return set()
                
                # Calculate priority
                priority = max(0.1, 0.8 - (depth * 0.1))
                
                # Add URL to sitemap data
                sitemap_urls.append({
                    'loc': url,
                    'lastmod': datetime.datetime.now().strftime('%Y-%m-%d'),
                    'changefreq': 'daily' if depth <= 1 else 'weekly',
                    'priority': f"{priority:.1f}"
                })
                
                # Find all links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    cleaned_url = clean_url(absolute_url, url)
                    
                    if (cleaned_url and 
                        cleaned_url not in visited and
                        not any(pattern in cleaned_url for pattern in config['exclude_patterns']) and
                        any(cleaned_url.endswith(ext) for ext in config['valid_extensions']) and
                        not re.search(r'\.(pdf|jpg|png|gif|zip|exe|docx)$', cleaned_url, re.I)):
                        new_urls.add((cleaned_url, depth + 1))
                
        except Exception as e:
            logging.error(f"Error crawling {url}: {e}")
    
    return new_urls

def generate_html_sitemap(sitemap_urls, output_dir):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sitemap</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { text-align: center; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            @media (max-width: 600px) { table, th, td { font-size: 14px; } }
        </style>
    </head>
    <body>
        <h1>Sitemap</h1>
        <table>
            <tr>
                <th>URL</th>
                <th>Last Modified</th>
                <th>Change Frequency</th>
                <th>Priority</th>
            </tr>
    """
    
    for url_data in sorted(sitemap_urls, key=lambda x: x['loc']):
        html_content += f"""
            <tr>
                <td><a href="{url_data['loc']}">{url_data['loc']}</a></td>
                <td>{url_data['lastmod']}</td>
                <td>{url_data['changefreq']}</td>
                <td>{url_data['priority']}</td>
            </tr>
        """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    html_filename = output_dir / 'sitemap.html'
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logging.getLogger(__name__).info(f"HTML sitemap generated at {html_filename}")

async def create_sitemap():
    config = load_config()
    
    try:
        # Get user input
        site_url = input("Enter the website URL (e.g., https://example.com): ").strip()
        site_url = validate_url(site_url)
        
        # Create output directory based on domain
        domain = urlparse(site_url).netloc
        output_dir = Path(domain)
        output_dir.mkdir(exist_ok=True)
        
        # Setup logging with output directory
        logger = setup_logging(output_dir)
        
        # Initialize
        global sitemap_urls
        sitemap_urls = []
        visited = set()
        limiter = AsyncLimiter(config['requests_per_second'], 1)
        
        async with aiohttp.ClientSession() as session:
            robots_parser = await check_robots_txt(site_url, session)
            
            # Start crawling
            tasks = [crawl_url(site_url, 0, session, robots_parser, visited, config, limiter)]
            
            while tasks:
                new_tasks = []
                for future in asyncio.as_completed(tasks):
                    new_urls = await future
                    new_tasks.extend([crawl_url(url, depth, session, robots_parser, visited, config, limiter) 
                                    for url, depth in new_urls])
                tasks = new_tasks
            
            # Generate sitemap(s)
            if not sitemap_urls:
                logger.warning("No URLs found to include in sitemap")
                print("No URLs found to include in sitemap")
                return
            
            # Generate HTML sitemap
            generate_html_sitemap(sitemap_urls, output_dir)
            
            # Split into multiple sitemaps if needed
            sitemap_chunks = [sitemap_urls[i:i + config['max_urls_per_sitemap']] 
                            for i in range(0, len(sitemap_urls), config['max_urls_per_sitemap'])]
            
            if len(sitemap_chunks) > 1:
                # Create sitemap index
                sitemap_index = ET.Element('sitemapindex', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
                
                for i, chunk in enumerate(sitemap_chunks, 1):
                    # Create individual sitemap
                    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
                    for url_data in sorted(chunk, key=lambda x: x['loc']):
                        url = ET.SubElement(urlset, 'url')
                        ET.SubElement(url, 'loc').text = url_data['loc']
                        ET.SubElement(url, 'lastmod').text = url_data['lastmod']
                        ET.SubElement(url, 'changefreq').text = url_data['changefreq']
                        ET.SubElement(url, 'priority').text = url_data['priority']
                    
                    sitemap_filename = output_dir / f"sitemap-{i}.xml"
                    tree = ET.ElementTree(urlset)
                    tree.write(sitemap_filename, encoding='utf-8', xml_declaration=True)
                    
                    # Compress sitemap
                    with open(sitemap_filename, 'rb') as f_in:
                        with gzip.open(sitemap_filename.with_suffix('.xml.gz'), 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    # Add to sitemap index
                    sitemap = ET.SubElement(sitemap_index, 'sitemap')
                    ET.SubElement(sitemap, 'loc').text = f"{site_url}/{sitemap_filename.name}.gz"
                    ET.SubElement(sitemap, 'lastmod').text = datetime.datetime.now().strftime('%Y-%m-%d')
                
                # Save sitemap index
                sitemap_index_filename = output_dir / 'sitemap.xml'
                tree = ET.ElementTree(sitemap_index)
                tree.write(sitemap_index_filename, encoding='utf-8', xml_declaration=True)
                
                logger.info(f"Sitemap index generated with {len(sitemap_chunks)} sitemaps containing {len(sitemap_urls)} URLs in {output_dir}")
                print(f"Sitemap index generated with {len(sitemap_chunks)} sitemaps containing {len(sitemap_urls)} URLs")
            
            else:
                # Create single sitemap
                urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
                for url_data in sorted(sitemap_urls, key=lambda x: x['loc']):
                    url = ET.SubElement(urlset, 'url')
                    ET.SubElement(url, 'loc').text = url_data['loc']
                    ET.SubElement(url, 'lastmod').text = url_data['lastmod']
                    ET.SubElement(url, 'changefreq').text = url_data['changefreq']
                    ET.SubElement(url, 'priority').text = url_data['priority']
                
                sitemap_filename = output_dir / 'sitemap.xml'
                tree = ET.ElementTree(urlset)
                tree.write(sitemap_filename, encoding='utf-8', xml_declaration=True)
                
                # Compress sitemap
                with open(sitemap_filename, 'rb') as f_in:
                    with gzip.open(sitemap_filename.with_suffix('.xml.gz'), 'wb') as f_out:
                        f_out.writelines(f_in)
                
                logger.info(f"Sitemap generated with {len(sitemap_urls)} URLs in {output_dir}")
                print(f"Sitemap generated with {len(sitemap_urls)} URLs")
            
            print(f"Compressed sitemap(s) saved as .gz files in {output_dir}")
            print(f"HTML sitemap saved as 'sitemap.html' in {output_dir}")
            print(f"Check '{output_dir / 'sitemap_generator.log'}' for detailed logs")
            
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        print(f"Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(create_sitemap())