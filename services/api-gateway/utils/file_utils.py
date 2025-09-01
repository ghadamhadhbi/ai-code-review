"""
File utility functions
Language detection, file stats, and validation helpers
"""

import re
import aiofiles
from click import FileError
import structlog
from pathlib import Path
from typing import Dict, Optional

logger = structlog.get_logger(__name__)

# Language detection patterns
LANGUAGE_PATTERNS = {
    # Extensions to language mapping
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.cxx': 'cpp',
    '.cc': 'cpp',
    '.c': 'c',
    '.h': 'c',
    '.hpp': 'cpp',
    '.go': 'go',
    '.rs': 'rust',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.cs': 'csharp',
    '.scala': 'scala',
    '.r': 'r',
    '.sql': 'sql',
    '.sh': 'bash',
    '.ps1': 'powershell',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.xml': 'xml',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
}

# Content-based detection patterns
CONTENT_PATTERNS = {
    'python': [
        r'^\s*import\s+\w+',
        r'^\s*from\s+\w+\s+import',
        r'^\s*def\s+\w+\s*\(',
        r'^\s*class\s+\w+\s*[:\(]',
        r'if\s+__name__\s*==\s*["\']__main__["\']',
    ],
    'javascript': [
        r'^\s*const\s+\w+\s*=',
        r'^\s*let\s+\w+\s*=',
        r'^\s*var\s+\w+\s*=',
        r'^\s*function\s+\w+\s*\(',
        r'console\.log\s*\(',
        r'require\s*\(["\']',
        r'module\.exports\s*=',
    ],
    'typescript': [
        r'^\s*interface\s+\w+\s*{',
        r'^\s*type\s+\w+\s*=',
        r':\s*\w+\s*=',
        r'^\s*export\s+interface',
        r'^\s*import.*from\s+["\']',
    ],
    'java': [
        r'^\s*package\s+\w+',
        r'^\s*import\s+java\.',
        r'^\s*public\s+class\s+\w+',
        r'^\s*private\s+\w+\s+\w+',
        r'System\.out\.println',
    ],
    'cpp': [
        r'^\s*#include\s*<\w+>',
        r'^\s*#include\s*"\w+"',
        r'^\s*using\s+namespace\s+std',
        r'std::\w+',
        r'cout\s*<<',
    ],
    'c': [
        r'^\s*#include\s*<\w+\.h>',
        r'^\s*int\s+main\s*\(',
        r'printf\s*\(',
        r'^\s*struct\s+\w+',
    ],
    'go': [
        r'^\s*package\s+\w+',
        r'^\s*import\s+\(',
        r'^\s*func\s+\w+\s*\(',
        r'fmt\.Print',
        r'^\s*type\s+\w+\s+struct',
    ],
    'rust': [
        r'^\s*use\s+\w+',
        r'^\s*fn\s+\w+\s*\(',
        r'^\s*struct\s+\w+',
        r'println!\s*\(',
        r'^\s*impl\s+\w+',
    ],
    'php': [
        r'^\s*<\?php',
        r'^\s*namespace\s+\w+',
        r'^\s*class\s+\w+',
        r'\$\w+\s*=',
        r'echo\s+',
    ],
    'ruby': [
        r'^\s*class\s+\w+',
        r'^\s*def\s+\w+',
        r'^\s*require\s+["\']',
        r'puts\s+',
        r'^\s*module\s+\w+',
    ],
}


def detect_language(filename: str, content: str) -> Optional[str]:
    """
    Detect programming language from filename and content
    
    Args:
        filename: Name of the file
        content: File content as string
        
    Returns:
        Detected language name or None
    """
    # First try extension-based detection
    extension = Path(filename).suffix.lower()
    if extension in LANGUAGE_PATTERNS:
        detected = LANGUAGE_PATTERNS[extension]
        logger.debug("Language detected by extension", filename=filename, language=detected)
        return detected
    
    # If extension detection fails, try content-based detection
    content_lines = content.split('\n')[:50]  # Check first 50 lines
    
    language_scores = {}
    
    for language, patterns in CONTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            for line in content_lines:
                if re.search(pattern, line, re.MULTILINE):
                    score += 1
        
        if score > 0:
            language_scores[language] = score
    
    if language_scores:
        # Return language with highest score
        detected = max(language_scores, key=language_scores.get)
        logger.debug(
            "Language detected by content",
            filename=filename,
            language=detected,
            score=language_scores[detected]
        )
        return detected
    
    logger.warning("Could not detect language", filename=filename)
    return None


async def get_file_stats(filepath: Path) -> Dict[str, int]:
    """
    Get file statistics (line count, character count)
    
    Args:
        filepath: Path to the file
        
    Returns:
        Dictionary with file statistics
    """
    try:
        async with aiofiles.open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
            
        lines = content.split('\n')
        
        # Count non-empty lines
        non_empty_lines = sum(1 for line in lines if line.strip())
        
        # Count characters (excluding whitespace-only lines)
        char_count = sum(len(line) for line in lines if line.strip())
        
        return {
            'line_count': len(lines),
            'non_empty_lines': non_empty_lines,
            'char_count': len(content),
            'char_count_no_whitespace': char_count,
        }
        
    except Exception as e:
        logger.error("Failed to get file stats", filepath=str(filepath), error=str(e))
        return {
            'line_count': 0,
            'non_empty_lines': 0,
            'char_count': 0,
            'char_count_no_whitespace': 0,
        }


def validate_filename(filename: str) -> bool:
    """
    Validate filename for security and format
    
    Args:
        filename: Original filename
        
    Returns:
        True if filename is valid
    """
    if not filename or len(filename) > 255:
        return False
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for null bytes
    if '\x00' in filename:
        return False
    
    # Must have an extension
    if '.' not in filename:
        return False
    
    return True


def is_text_file(content: bytes) -> bool:
    """
    Check if file content appears to be text
    
    Args:
        content: File content as bytes
        
    Returns:
        True if content appears to be text
    """
    try:
        # Try to decode as UTF-8
        content.decode('utf-8')
        
        # Check for null bytes (binary indicator)
        if b'\x00' in content:
            return False
        
        # Check ratio of printable characters
        text_chars = sum(1 for byte in content if 32 <= byte <= 126 or byte in [9, 10, 13])
        
        if len(content) == 0:
            return True
        
        text_ratio = text_chars / len(content)
        return text_ratio > 0.7  # At least 70% printable characters
        
    except UnicodeDecodeError:
        return False


async def read_file_safely(filepath: Path, max_size_mb: int = 10) -> str:
    """
    Safely read file content with size limits
    
    Args:
        filepath: Path to file
        max_size_mb: Maximum file size in MB
        
    Returns:
        File content as string
    """
    try:
        file_size = filepath.stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise FileError(f"File too large: {file_size} bytes (max: {max_size_bytes})")
        
        async with aiofiles.open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return await f.read()
            
    except Exception as e:
        logger.error("Failed to read file safely", filepath=str(filepath), error=str(e))
        raise FileError(f"Failed to read file: {str(e)}")


def get_language_info(language: str) -> Dict[str, str]:
    """
    Get additional information about a programming language
    
    Args:
        language: Programming language name
        
    Returns:
        Dictionary with language information
    """
    language_info = {
        'python': {
            'name': 'Python',
            'category': 'interpreted',
            'paradigm': 'multi-paradigm',
            'typical_extensions': ['.py', '.pyw'],
        },
        'javascript': {
            'name': 'JavaScript',
            'category': 'interpreted',
            'paradigm': 'multi-paradigm',
            'typical_extensions': ['.js', '.jsx'],
        },
        'typescript': {
            'name': 'TypeScript',
            'category': 'compiled',
            'paradigm': 'multi-paradigm',
            'typical_extensions': ['.ts', '.tsx'],
        },
        'java': {
            'name': 'Java',
            'category': 'compiled',
            'paradigm': 'object-oriented',
            'typical_extensions': ['.java'],
        },
        'cpp': {
            'name': 'C++',
            'category': 'compiled',
            'paradigm': 'multi-paradigm',
            'typical_extensions': ['.cpp', '.cxx', '.cc', '.hpp'],
        },
        'c': {
            'name': 'C',
            'category': 'compiled',
            'paradigm': 'procedural',
            'typical_extensions': ['.c', '.h'],
        },
        'go': {
            'name': 'Go',
            'category': 'compiled',
            'paradigm': 'procedural',
            'typical_extensions': ['.go'],
        },
        'rust': {
            'name': 'Rust',
            'category': 'compiled',
            'paradigm': 'multi-paradigm',
            'typical_extensions': ['.rs'],
        },
    }
    
    return language_info.get(language.lower(), {
        'name': language.title(),
        'category': 'unknown',
        'paradigm': 'unknown',
        'typical_extensions': [],
    })