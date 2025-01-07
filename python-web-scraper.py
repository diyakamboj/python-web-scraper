import os
import requests
from bs4 import BeautifulSoup, NavigableString
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from colorama import Fore, init
import argparse
import string

# Initialize colorama
init(autoreset=True)

def save_text_to_file(text, output_file, last_content):
    try:
        if text.strip() and text.strip() != last_content:
            output_file.write(text + '\n')
            last_content = text.strip()
        return last_content
    except Exception as e:
        print(Fore.RED + f"Error saving text to file: {e}")
        return last_content

def get_domain_name(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain.replace('www.', '')

def is_clean_content(text):
    try:
        cleaned_text = text.translate(str.maketrans('', '', string.punctuation)).lower()
        words = cleaned_text.split()
        if len(words) < 2:
            return False
        alphanumeric_ratio = sum(c.isalnum() for c in cleaned_text) / len(cleaned_text) if cleaned_text else 0
        return alphanumeric_ratio > 0.5
    except Exception as e:
        print(Fore.RED + f"Error checking if text is meaningful: {e}")
        return False

def extract_content_from_url(url, output_file):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        last_content = ""

        title = soup.title.string if soup.title else "No title found"
        last_content = save_text_to_file(f"Title: {title}\n", output_file, last_content)

        main_content = soup.body or soup

        for element in main_content.descendants:
            if isinstance(element, NavigableString):
                continue

            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                header_text = element.text.strip()
                if len(header_text) > 1 and not header_text.isdigit() and is_clean_content(header_text):
                    last_content = save_text_to_file(f"\n{element.name.upper()}: {header_text}", output_file, last_content)
            elif element.name == 'p':
                paragraph_text = element.text.strip()
                if is_clean_content(paragraph_text):
                    last_content = save_text_to_file(paragraph_text, output_file, last_content)
            elif element.name == 'ul':
                items = [li.text.strip() for li in element.find_all('li', recursive=False)]
                if is_clean_content(", ".join(items)):
                    last_content = save_text_to_file("Unordered List: " + ", ".join(items), output_file, last_content)
            elif element.name == 'ol':
                items = [li.text.strip() for li in element.find_all('li', recursive=False)]
                if is_clean_content(", ".join(items)):
                    last_content = save_text_to_file("Ordered List: " + ", ".join(items), output_file, last_content)
    except Exception as e:
        print(Fore.RED + f"Error extracting content from {url}: {e}")

def fetch_sitemap_urls(base_url):
    try:
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap/',
            '/sitemap.php',
            '/sitemap.txt'
        ]

        for path in sitemap_paths:
            sitemap_url = urljoin(base_url, path)
            try:
                response = requests.get(sitemap_url)
                response.raise_for_status()

                if 'xml' in response.headers.get('Content-Type', '').lower():
                    root = ET.fromstring(response.content)
                    urls = [url.text for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                    if urls:
                        print(Fore.GREEN + f"Sitemap found at: {sitemap_url}")
                        return urls
            except requests.RequestException as e:
                print(Fore.RED + f"Error accessing {sitemap_url}: {e}")
            except ET.ParseError:
                print(Fore.RED + f"Error parsing XML from {sitemap_url}")

        print(Fore.YELLOW + f"No sitemap found. Scraping the provided URL: {base_url}")
        return [base_url]
    except Exception as e:
        print(Fore.RED + f"Error fetching sitemap URLs: {e}")
        return []

def group_urls(urls):
    try:
        groups = defaultdict(list)
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            parts = path.split('/')
            if len(parts) > 1:
                group = parts[0]
            else:
                group = 'root'
            groups[group].append(url)
        return groups
    except Exception as e:
        print(Fore.RED + f"Error grouping URLs: {e}")
        return defaultdict(list)

def main():
    parser = argparse.ArgumentParser(description="Web Scraper")
    parser.add_argument('base_url', type=str, help='The base URL of the website to scrape')
    args = parser.parse_args()

    base_url = args.base_url
    sitemap_urls = fetch_sitemap_urls(base_url)
    grouped_urls = group_urls(sitemap_urls)
    domain_name = get_domain_name(args.url)
    output_filename = os.path.join(os.getcwd(), f"{domain_name}_{group}_content.txt")

    try:
        with open(output_filename, 'w', encoding='utf-8') as output_file:
            for group, urls in grouped_urls.items():
                for url in urls:
                    print(Fore.BLUE + f"Scraping: {url}")
                    output_file.write(f"\n\n--- Content from: {url} ---\n\n")
                    extract_content_from_url(url, output_file)
        print(Fore.GREEN + f"Content has been saved to {output_filename}")
    except Exception as e:
        print(Fore.RED + f"Error writing to output file: {e}")

if __name__ == "__main__":
    main()
