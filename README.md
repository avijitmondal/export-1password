# export-1password

A Python utility to convert 1Password exported files (.1pux) to CSV format for import into various password managers.

## Features

- Converts 1Password .1pux files to multiple password manager formats
- Support for iCloud Passwords format (more formats coming soon)
- Robust error handling and logging
- Command-line interface with argument parsing
- Secure temporary file handling
- Comprehensive validation and error messages

## Installation

1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd export-1password
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Basic Usage

```bash
python main.py /path/to/your/export.1pux
```

### Advanced Usage

```bash
# Specify output directory
python main.py /path/to/your/export.1pux -o /path/to/output/

# Specify output format (currently supports: icloud)
python main.py /path/to/your/export.1pux -f icloud

# Enable verbose logging
python main.py /path/to/your/export.1pux -v

# Combine options
python main.py /path/to/your/export.1pux -f icloud -o /path/to/output/ -v

# Show help
python main.py --help
```

## Output Formats

### iCloud Passwords (default)
The generated CSV file contains the following columns:
- Title
- URL
- Username
- Password
- Notes
- OTPAuth

## Command Line Options

- `input_file`: Path to the 1Password .1pux file (required)
- `-o, --output-dir`: Output directory for the CSV file (default: same as input file)
- `-f, --format`: Output format for password manager (default: icloud, choices: icloud)
- `-v, --verbose`: Enable verbose logging
- `-h, --help`: Show help message

## Security Considerations

- Temporary files are automatically cleaned up
- Use secure file permissions for exported CSV files
- Consider encrypting or securely deleting CSV files after import

## Error Handling

The script provides detailed error messages for common issues:
- Missing or invalid input files
- Corrupted 1Password archives
- Invalid JSON data
- File system errors

## Requirements

- Python 3.7+
- See `requirements.txt` for dependencies

## License

[Add your license information here]