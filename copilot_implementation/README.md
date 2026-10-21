# Copilot implementation (from PR #1)

A program to download the user manuals page by page from their interactive websites.

This folder contains the implementation written by GitHub Copilot in PR #1. It is kept separate from the root implementation (`../kawasaki_manual_downloader.py`) so the two can be run and compared independently. Everything here uses its own `requirements.txt` and writes to its own output folder, `copilot_implementation/output/`, so it never touches the repo's `manuals/` folder. See the main [README](../README.md) for a comparison of the two implementations.

## ⚠️ Known limitations (tested 2026-10-20 on the KX450 manual)

**On the KX450 manual URL, this implementation currently downloads no pages.** Tested with Chrome 155 and selenium 4.51.0:

- `python kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN" -m 2` ran for 407 s, exited with code 0, and logged "Download completed. Processed 2 pages." But it saved **0 images**.
- After moving it into this folder: `python copilot_implementation/kawasaki_downloader.py "<KX450 URL>" -m 1`, run from the repo root, took 207.6 s, exited with code 0, created `copilot_implementation/output/`, and saved **0 images**.
- Every loop iteration logs `ERROR - Error processing page 1: Message: invalid selector: An invalid or illegal selector was specified`. The navigation-button selectors include `button:contains("Next")` / `a:contains("Previous")`. `:contains()` is jQuery-only and isn't valid CSS, so Selenium raises an exception, and the loop just moves on to the next iteration without navigating.
- The page images aren't found either. The viewer loads the flip-book from a separate document (`/assets/manuals/<book>/index.html`), and the script only searches the top-level page.
- Each iteration takes about 2.5 to 3.5 minutes, because the 10 s implicit wait applies to every selector that isn't found. A run with the default `-m 100` was stopped after about 4 minutes with 0 images. A full default run was not measured.
- The program saves page images only. It doesn't make a PDF.

The tests (`python -m unittest test_kawasaki`) and `validate_installation.py` pass. They only check imports, setup, and helper logic, not a real download.

## Features

- Automatically navigates through manual pages using arrow controls
- Downloads high-quality images of each page
- Handles various website layouts and image formats
- Supports headless operation for automation
- Robust error handling and retry logic
- Progress tracking and logging

## Installation

1. Clone this repository and go into this folder:
   ```bash
   git clone https://github.com/ElectricRCAircraftGuy/Kawasaki.git
   cd Kawasaki/copilot_implementation
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

If you prefer to install dependencies manually (a virtual environment is recommended, separate from the root implementation's):

```bash
cd copilot_implementation
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

You'll also need Chrome browser installed on your system.

## Usage

### Basic Usage

Run from this folder (or give the path, e.g. `python copilot_implementation/kawasaki_downloader.py <URL>` from the repo root):

```bash
python kawasaki_downloader.py <URL>
```

### Tests

```bash
python -m unittest test_kawasaki     # from this folder
python validate_installation.py
```

### Example

```bash
python kawasaki_downloader.py "https://pws.ktivs.net/dispeBook?file=99803-0401&lang_code=EN"
```

### Advanced Options

```bash
python kawasaki_downloader.py <URL> [OPTIONS]

Options:
  -o, --output DIR          Output directory for downloaded images (default: copilot_implementation/output/)
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

Downloaded images go into `copilot_implementation/output/` by default (ignored by git), no matter which directory you run the script from. Use `-o` to choose another folder. Files are saved with sequential filenames:
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

This code is licensed under the GPL-3.0 License - see the repo's [LICENSE](../LICENSE) file for details. Downloaded manuals and pages are copyrighted by Kawasaki and are not covered by that license (see the main [README](../README.md)).

## Legal Notice

This tool is for personal use and educational purposes. Please respect website terms of service and copyright laws. Only download content you have permission to access.
