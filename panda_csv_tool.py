"""
Panda CSV Analysis Tool

Enables row-by-row CSV processing with flexible column referencing.
Integrates seamlessly with existing chatbot workflow.

Syntax:
  {CX}   - Read from column X (input)
  {{CX}} - Write to column X (output)
"""

import pandas as pd
import re
import os
from typing import Optional, Dict, List, Tuple, Any


class PandaCSVAnalysisTool:
    """
    Manages CSV loading, prompt processing, and result writing.
    Preserves all existing chatbot settings and tool integrations.
    """
    
    def __init__(self):
        """Initialize the CSV analysis tool."""
        self.csv_data: Optional[pd.DataFrame] = None
        self.csv_path: Optional[str] = None
        self.original_headers: List[str] = []
        self.num_rows: int = 0
        self.num_cols: int = 0
        self.is_active: bool = False
        self.rows_processed: int = 0
        self.rows_updated: int = 0
        
    def load_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Load a CSV file and prepare it for processing.
        
        Args:
            file_path: Absolute path to the CSV file
            
        Returns:
            dict: Metadata about the loaded CSV
                {
                    "success": bool,
                    "rows": [start, end],
                    "cols": [start, end],
                    "headers": List[str],
                    "error": str (if success=False)
                }
        """
        try:
            # Load CSV
            self.csv_data = pd.read_csv(file_path)
            self.csv_path = file_path
            
            # Store original headers
            self.original_headers = list(self.csv_data.columns)
            
            # Relabel columns numerically (1, 2, 3...)
            self.csv_data.columns = range(1, len(self.csv_data.columns) + 1)
            
            # Store metadata
            self.num_rows = len(self.csv_data)
            self.num_cols = len(self.csv_data.columns)
            self.is_active = True
            self.rows_processed = 0
            self.rows_updated = 0
            
            return {
                "success": True,
                "rows": [2, self.num_rows + 1],  # Row 1 is header, data starts at 2
                "cols": [1, self.num_cols],
                "headers": self.original_headers,
                "total_rows": self.num_rows,
                "total_cols": self.num_cols
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        except pd.errors.EmptyDataError:
            return {
                "success": False,
                "error": "CSV file is empty"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error loading CSV: {str(e)}"
            }
    
    def clear(self):
        """Clear all loaded CSV data and reset state."""
        self.csv_data = None
        self.csv_path = None
        self.original_headers = []
        self.num_rows = 0
        self.num_cols = 0
        self.is_active = False
        self.rows_processed = 0
        self.rows_updated = 0
    
    def has_data(self) -> bool:
        """Check if CSV data is loaded."""
        return self.csv_data is not None and self.is_active
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get current CSV metadata."""
        if not self.has_data():
            return {"loaded": False}
        
        return {
            "loaded": True,
            "file_path": self.csv_path,
            "rows": self.num_rows,
            "cols": self.num_cols,
            "headers": self.original_headers,
            "original_headers": self.original_headers,
            "rows_processed": self.rows_processed,
            "rows_updated": self.rows_updated
        }
    
    def extract_row_specification(self, prompt: str) -> Tuple[Optional[str], str]:
        """
        Extract row specification from prompt.
        
        Args:
            prompt: The prompt text potentially containing {R...}
            
        Returns:
            tuple: (row_spec or None, cleaned_prompt without {R...})
            
        Example:
            "{R1-5} Grade these answers" → ("1-5", "Grade these answers")
            "Grade all answers" → (None, "Grade all answers")
        """
        # Pattern: {R followed by row spec} - matches {R1}, {R1-5}, {R1,3,5}, etc.
        pattern = r'\{R([^}]+)\}'
        match = re.search(pattern, prompt)
        
        if match:
            row_spec = match.group(1).strip()
            # Remove the {R...} from prompt
            cleaned_prompt = re.sub(pattern, '', prompt).strip()
            return row_spec, cleaned_prompt
        
        return None, prompt
    
    def process_prompt_for_row(self, user_prompt: str, row_idx: int) -> Tuple[str, List[int], Dict[str, str]]:
        """
        Process user prompt for a specific row by substituting column references.
        
        Args:
            user_prompt: Raw user prompt with {CX} and {{CX}} references
            row_idx: 0-based row index in the DataFrame
            
        Returns:
            Tuple containing:
                - processed_prompt: Prompt with substitutions for the model
                - output_columns: List of column indices to expect in response
                - substitutions: Dict of what was substituted (for logging)
        
        Syntax:
            {CX}   - INPUT: Read from column X, substitute with actual value
            {{CX}} - OUTPUT: Write to column X, convert to COLUMN_X marker
        
        Example:
            Input:  "Grade {C4} based on {C3}. Write to {{C5}} and {{C6}}."
            Output: "Grade 'Four' based on 'What is 2+2?'. Write to COLUMN_5 and COLUMN_6."
                    [5, 6], {"C3": "What is 2+2?", "C4": "Four"}
        """
        if not self.has_data():
            raise ValueError("No CSV data loaded")
        
        if row_idx < 0 or row_idx >= self.num_rows:
            raise IndexError(f"Row index {row_idx} out of range (0-{self.num_rows-1})")
        
        processed_prompt = user_prompt
        output_columns = []
        substitutions = {}
        
        # Step 1: Process OUTPUT columns (double braces) FIRST
        # Use regex to find all {{CX}} patterns
        output_pattern = r'\{\{C(\d+)\}\}'
        output_refs = re.findall(output_pattern, user_prompt)
        
        for col_num in output_refs:
            col_idx = int(col_num)
            output_columns.append(col_idx)
            
            # Replace {{CX}} with COLUMN_X for model clarity
            processed_prompt = processed_prompt.replace(
                f"{{{{C{col_num}}}}}", 
                f"COLUMN_{col_num}"
            )
            substitutions[f"{{C{col_num}}}"] = f"COLUMN_{col_num}"
        
        # Step 2: Process INPUT columns (single braces)
        # Note: We've already replaced {{}} above, so only single braces remain
        input_pattern = r'\{C(\d+)\}'
        input_refs = re.findall(input_pattern, processed_prompt)
        
        for col_num in input_refs:
            col_idx = int(col_num)
            
            # Get cell value
            cell_value = self._get_cell_value(row_idx, col_idx)
            
            # Substitute in prompt
            processed_prompt = processed_prompt.replace(
                f"{{C{col_num}}}", 
                f"'{cell_value}'"
            )
            substitutions[f"C{col_num}"] = cell_value
        
        return processed_prompt, output_columns, substitutions
    
    def _get_cell_value(self, row_idx: int, col_idx: int) -> str:
        """
        Get formatted cell value from DataFrame.
        
        Args:
            row_idx: 0-based row index
            col_idx: 1-based column index (as stored in DataFrame)
            
        Returns:
            str: Formatted cell value
        """
        if col_idx > self.num_cols:
            return "[Column does not exist]"
        
        try:
            cell_value = self.csv_data.at[row_idx, col_idx]
            
            # Handle NaN, None, and empty strings
            if pd.isna(cell_value):
                return "[Empty]"
            
            cell_str = str(cell_value).strip()
            if cell_str == "":
                return "[Empty]"
            
            return cell_str
            
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    def parse_model_response(self, response: str, expected_columns: List[int]) -> Dict[int, str]:
        """
        Parse model response for COLUMN_X: value patterns.
        
        Args:
            response: Raw model response text
            expected_columns: List of column indices we expect to find
            
        Returns:
            dict: {column_index: value} mapping
        
        Example:
            Input:  "The answer is correct.\nCOLUMN_5: 3.0\nCOLUMN_6: Well done!"
            Output: {5: "3.0", 6: "Well done!"}
        """
        updates = {}
        
        # Pattern: COLUMN_X: value (capture everything after colon until newline or end)
        pattern = r'COLUMN[_\s](\d+):\s*(.+?)(?:\n|$)'
        
        matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            col_num = int(match.group(1))
            value = match.group(2).strip()
            
            # Only accept expected columns (prevents accidental writes)
            if col_num in expected_columns:
                updates[col_num] = value
        
        return updates
    
    def update_cell(self, row_idx: int, col_idx: int, value: str) -> bool:
        """
        Update a cell in the DataFrame.
        
        Args:
            row_idx: 0-based row index
            col_idx: 1-based column index
            value: Value to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.has_data():
            return False
        
        try:
            # Create column if it doesn't exist
            if col_idx > self.num_cols:
                # Add missing columns
                for new_col in range(self.num_cols + 1, col_idx + 1):
                    self.csv_data[new_col] = ""
                self.num_cols = col_idx
            
            # Update cell
            self.csv_data.at[row_idx, col_idx] = value
            return True
            
        except Exception as e:
            print(f"Error updating cell [{row_idx}, {col_idx}]: {e}")
            return False
    
    def save_csv(self, output_path: Optional[str] = None) -> bool:
        """
        Save the DataFrame back to CSV.
        
        Args:
            output_path: Optional custom output path. If None, overwrites original file.
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.has_data():
            return False
        
        try:
            # Use original path if no output specified
            save_path = output_path or self.csv_path
            
            # Restore original headers (first N columns) and add generic names for new columns
            restored_headers = []
            for col_idx in range(1, self.num_cols + 1):
                if col_idx - 1 < len(self.original_headers):
                    restored_headers.append(self.original_headers[col_idx - 1])
                else:
                    restored_headers.append(f"Column_{col_idx}")
            
            # Create a copy with original headers
            output_df = self.csv_data.copy()
            output_df.columns = restored_headers
            
            # Save
            output_df.to_csv(save_path, index=False)
            return True
            
        except Exception as e:
            print(f"Error saving CSV: {e}")
            return False
    
    def get_row_summary(self, row_idx: int, max_cols: int = 5) -> str:
        """
        Get a human-readable summary of a row for display.
        
        Args:
            row_idx: 0-based row index
            max_cols: Maximum columns to display (truncate if more)
            
        Returns:
            str: Formatted row summary
        """
        if not self.has_data():
            return "[No data loaded]"
        
        if row_idx < 0 or row_idx >= self.num_rows:
            return "[Invalid row index]"
        
        summary_parts = []
        display_cols = min(max_cols, self.num_cols)
        
        for col_idx in range(1, display_cols + 1):
            header = self.original_headers[col_idx - 1] if col_idx - 1 < len(self.original_headers) else f"Col{col_idx}"
            value = self._get_cell_value(row_idx, col_idx)
            
            # Truncate long values
            if len(value) > 30:
                value = value[:27] + "..."
            
            summary_parts.append(f"  C{col_idx} ({header}): {value}")
        
        if self.num_cols > max_cols:
            summary_parts.append(f"  ... and {self.num_cols - max_cols} more columns")
        
        return "\n".join(summary_parts)


# Utility functions

def parse_column_ref(ref: str) -> int:
    """
    Parse a column reference string to numeric index.
    
    Args:
        ref: Column reference (e.g., "C3", "3", "Question")
        
    Returns:
        int: 1-based column index
        
    Raises:
        ValueError: If reference is invalid
    """
    # Try direct numeric
    if ref.isdigit():
        return int(ref)
    
    # Try CX format
    if ref.upper().startswith('C') and ref[1:].isdigit():
        return int(ref[1:])
    
    raise ValueError(f"Invalid column reference: {ref}")


def parse_row_specification(spec: str, total_rows: int) -> List[int]:
    """
    Parse row specification string into list of row indices (0-based).
    
    Supported formats:
        {R1}      - Single row (1-indexed input → 0-indexed output)
        {R1-5}    - Range from row 1 to 5 inclusive
        {R1,3,5}  - Specific rows 1, 3, and 5
        {R5-}     - From row 5 to end
        {R-5}     - From start to row 5
        {R1-3,7,9-11} - Mixed ranges and singles
    
    Args:
        spec: Row specification string (e.g., "1-5", "1,3,5", "5-")
        total_rows: Total number of rows in CSV
        
    Returns:
        List[int]: List of 0-based row indices
        
    Raises:
        ValueError: If specification is invalid
    """
    rows = set()
    
    # Split by comma for multiple parts
    parts = spec.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # Range specification
            range_parts = part.split('-', 1)
            
            if range_parts[0] == '':
                # {R-5} - from start to N
                start = 1
                end = int(range_parts[1])
            elif range_parts[1] == '':
                # {R5-} - from N to end
                start = int(range_parts[0])
                end = total_rows
            else:
                # {R5-10} - from N to M
                start = int(range_parts[0])
                end = int(range_parts[1])
            
            # Validate range
            if start < 1 or end > total_rows or start > end:
                raise ValueError(f"Invalid row range: {part} (total rows: {total_rows})")
            
            # Add all rows in range (convert to 0-based)
            for i in range(start - 1, end):
                rows.add(i)
        else:
            # Single row specification
            row_num = int(part)
            if row_num < 1 or row_num > total_rows:
                raise ValueError(f"Row {row_num} out of range (total rows: {total_rows})")
            rows.add(row_num - 1)  # Convert to 0-based
    
    return sorted(list(rows))


def format_cell_value(value: Any, max_length: int = 50) -> str:
    """
    Format a cell value for display.
    
    Args:
        value: Raw cell value
        max_length: Maximum display length
        
    Returns:
        str: Formatted value
    """
    if pd.isna(value):
        return "[Empty]"
    
    str_value = str(value).strip()
    
    if str_value == "":
        return "[Empty]"
    
    if len(str_value) > max_length:
        return str_value[:max_length - 3] + "..."
    
    return str_value
