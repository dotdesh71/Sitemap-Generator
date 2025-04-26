# Sitemap Generator (XML/HTML)
Sitemap Generator is a Python-based tool designed to crawl a website and create Google-friendly sitemaps in both XML and HTML formats. The tool respects robots.txt, handles canonical URLs, and organizes output files in a domain-specific folder. It supports large sites by generating sitemap indexes and compresses sitemaps using gzip for efficient storage and distribution. The HTML sitemap is styled for user readability and search engine compatibility, making it ideal for SEO purposes.

## Features
- Crawls websites asynchronously using `aiohttp` for speed.
- Generates XML sitemaps compliant with the sitemap protocol (http://www.sitemaps.org/schemas/sitemap/0.9).
- Creates a user-friendly HTML sitemap with clickable URLs and metadata.
- Organizes output in a folder named after the website's domain (e.g., `www.example.com`).
- Supports sitemap indexes for sites with more than 50,000 URLs.
- Compresses sitemaps using gzip.
- Respects robots.txt and canonical URLs.
- Configurable via a `sitemap_config.yaml` file for crawl depth, exclusions, and more.
- Detailed logging for debugging and monitoring.

## Requirements
- Python 3.7 or higher
- Required Python packages:
  - `aiohttp`
  - `aiolimiter`
  - `pyyaml`
  - `validators`
  - `beautifulsoup4`

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/dotdesh71/sitemap-generator.git
   cd sitemap-generator
   ```
2. Install the required packages:
   ```bash
   pip install aiohttp aiolimiter pyyaml validators beautifulsoup4
   ```
3. Ensure the `sitemap_config.yaml` file is in the project directory. A default configuration is provided:
   ```yaml
   max_urls_per_sitemap: 50000
   max_concurrent_requests: 10
   requests_per_second: 2
   max_depth: 3
   exclude_patterns:
     - login
     - admin
     - wp-admin
     - logout
   valid_extensions:
     - .html
     - .php
     - .asp
     - .aspx
     - ''
   ```

## Usage
1. Run the script:
   ```bash
   python sitemap_generator.py
   ```
2. Enter the website URL when prompted (e.g., `https://www.example.com`).
3. The tool will:
   - Crawl the website, respecting robots.txt and canonical URLs.
   - Create a folder named after the domain (e.g., `www.example.com`).
   - Generate `sitemap.xml`, `sitemap.xml.gz`, and `sitemap.html` in the folder.
   - For large sites, additional sitemaps (`sitemap-1.xml`, etc.) and a sitemap index may be created.
   - Save logs to `sitemap_generator.log` in the domain folder.

4. Check the output folder for the generated files:
   - `sitemap.xml`: Main sitemap or sitemap index.
   - `sitemap.html`: User-friendly HTML sitemap with clickable URLs.
   - `sitemap.xml.gz`: Compressed sitemap.
   - `sitemap_generator.log`: Detailed logs.

## Example
```bash
$ python sitemap_generator.py
Enter the website URL (e.g., https://example.com): https://www.dotdesh.com
Sitemap generated with 150 URLs
Compressed sitemap(s) saved as .gz files in www.dotdesh.com
HTML sitemap saved as 'sitemap.html' in www.dotdesh.com
Check 'www.dotdesh.com\sitemap_generator.log' for detailed logs
```

## Configuration
Edit `sitemap_config.yaml` to customize:
- `max_urls_per_sitemap`: Maximum URLs per sitemap file (default: 50,000).
- `max_concurrent_requests`: Maximum concurrent HTTP requests (default: 10).
- `requests_per_second`: Rate limit for requests (default: 2).
- `max_depth`: Maximum crawl depth (default: 3).
- `exclude_patterns`: URL patterns to skip (e.g., login pages).
- `valid_extensions`: Allowed file extensions for crawled URLs.

## Troubleshooting
- **No URLs Found**: Check `sitemap_generator.log` for errors (e.g., HTTP 403, 429). The site may block bots or have no crawlable HTML pages. Test with `https://example.com`.
- **Missing Dependencies**: Ensure all required packages are installed (`pip install -r requirements.txt` if a `requirements.txt` is added).
- **Permission Issues**: Verify write permissions in the output directory.
- **Site-Specific Issues**: Some sites may require adjusting `exclude_patterns` or `valid_extensions` in `sitemap_config.yaml`.

## Contributing
Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact
For issues or suggestions, open an issue on GitHub or contact [your-email@example.com](mailto:your-email@example.com).
