#!/usr/bin/env python3
"""
Example usage of the Kawasaki Downloader

This script shows how to use the KawasakiDownloader class programmatically.
"""

import sys
from pathlib import Path
from kawasaki_downloader import KawasakiDownloader

def download_example_manual():
    """Download an example manual with custom settings."""
    
    # Example URL (replace with actual manual URL)
    manual_url = "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"
    
    # Custom output directory
    output_dir = "my_manual_download"
    
    print("Kawasaki Manual Downloader Example")
    print("=" * 35)
    print(f"URL: {manual_url}")
    print(f"Output Directory: {output_dir}")
    print()
    
    try:
        # Create downloader with custom settings
        with KawasakiDownloader(output_dir=output_dir, headless=True) as downloader:
            print("Starting download...")
            downloader.download_manual(manual_url, max_pages=10)  # Limit to 10 pages for demo
            
        print("\nDownload completed!")
        print(f"Check the '{output_dir}' folder for downloaded images.")
        
    except Exception as e:
        print(f"Error during download: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Chrome browser is installed")
        print("2. Run 'python setup.py' to install ChromeDriver")
        print("3. Check your internet connection")
        print("4. Try running with --no-headless for debugging")

def show_usage_examples():
    """Show various usage examples."""
    print("Kawasaki Downloader Usage Examples")
    print("=" * 35)
    print()
    
    print("1. Basic usage:")
    print("   python kawasaki_downloader.py \"<URL>\"")
    print()
    
    print("2. Custom output directory:")
    print("   python kawasaki_downloader.py \"<URL>\" -o \"my_folder\"")
    print()
    
    print("3. Limit number of pages:")
    print("   python kawasaki_downloader.py \"<URL>\" -m 20")
    print()
    
    print("4. Debug mode (visible browser):")
    print("   python kawasaki_downloader.py \"<URL>\" --no-headless")
    print()
    
    print("5. Verbose logging:")
    print("   python kawasaki_downloader.py \"<URL>\" -v")
    print()
    
    print("6. Combination of options:")
    print("   python kawasaki_downloader.py \"<URL>\" -o \"manual\" -m 50 -v")
    print()

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_usage_examples()
    else:
        print("To see usage examples, run: python example_usage.py --examples")
        print("To try the download (requires Chrome): python example_usage.py")
        print()
        
        # Uncomment the line below to actually try downloading
        # download_example_manual()
        
        print("Note: Actual download is commented out in this example.")
        print("Edit this file to enable the download test.")

if __name__ == "__main__":
    main()