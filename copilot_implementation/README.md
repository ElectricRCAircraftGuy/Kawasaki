# Kawasaki

A program to download the user manuals page by page from their interactive websites.

## Features

- Automatically navigates through manual pages using arrow controls
- Downloads high-quality images of each page
- Handles various website layouts and image formats
- Supports headless operation for automation
- Robust error handling and retry logic
- Progress tracking and logging

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ElectricRCAircraftGuy/Kawasaki.git
   cd Kawasaki
   ```

2. Run the setup script:
   ```bash
   python setup.py
   ```

3. Validate the installation:
   ```bash
   python validate_installation.py
   ```

This will install all required dependencies and set up the Chrome WebDriver automatically.

### Manual Installation

If you prefer to install dependencies manually:

```bash
pip install -r requirements.txt
```

You'll also need Chrome browser installed on your system.

## Usage

### Basic Usage

```bash
python kawasaki_downloader.py <URL>
```

### Example

```bash
python kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"
```

### Advanced Options

```bash
python kawasaki_downloader.py <URL> [OPTIONS]

Options:
  -o, --output DIR          Output directory for downloaded images (default: manual_pages)
  -m, --max-pages NUM       Maximum number of pages to download (default: 100)
  --no-headless            Run browser in visible mode (useful for debugging)
  -v, --verbose            Enable verbose logging
  -h, --help               Show this help message
```

### Examples

```bash
# Download to a specific folder
python kawasaki_downloader.py "URL" -o "my_manual"

# Limit to 50 pages
python kawasaki_downloader.py "URL" -m 50

# Run with visible browser for debugging
python kawasaki_downloader.py "URL" --no-headless

# Enable verbose logging
python kawasaki_downloader.py "URL" -v
```

## How It Works

1. **Page Loading**: Opens the manual URL in a Chrome browser
2. **Image Detection**: Identifies the main page image using various selectors
3. **Image Download**: Downloads the page image to the specified folder
4. **Navigation**: Finds and clicks the "next" button/arrow control
5. **Repeat**: Continues until no more pages are found or max limit reached

## Supported Formats

- JPEG/JPG images
- PNG images
- GIF images
- Canvas-rendered content (converted to PNG)
- Various interactive manual websites

## Output

Downloaded images are saved with sequential filenames:
- `page_0001.jpg`
- `page_0002.png`
- `page_0003.jpg`
- etc.

## Troubleshooting

### Common Issues

1. **Chrome not found**: Make sure Chrome browser is installed
2. **WebDriver issues**: Run `python setup.py` to reinstall
3. **Access denied**: Some sites may block automated access
4. **No images found**: The site might use a different layout - try `--no-headless` to debug

### Debug Mode

Run with `--no-headless` to see what the browser is doing:

```bash
python kawasaki_downloader.py "URL" --no-headless -v
```

## Additional Scripts

### validate_installation.py
Validates that all components are properly installed and working:
```bash
python validate_installation.py
```

### example_usage.py
Shows usage examples and demonstrates programmatic usage:
```bash
python example_usage.py --examples
```

### setup.py
Automated setup script for dependencies and ChromeDriver:
```bash
python setup.py
```

## Requirements

- Python 3.6+
- Chrome browser
- Internet connection

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Legal Notice

This tool is for personal use and educational purposes. Please respect website terms of service and copyright laws. Only download content you have permission to access.
