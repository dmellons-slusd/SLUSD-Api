#!/usr/bin/env python3
"""
Standalone script for processing IEP documents from command line
This maintains the original functionality from iep_at_a_glance.py for direct execution
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from slusdlib import core, aeries
from config import get_settings
from services.sped_service import SPEDService

def main():
    """Main function for standalone IEP processing"""
    settings = get_settings()
    
    core.log("~" * 80)
    if settings.TEST_RUN:
        core.log("Running in test mode. No changes will be made to the database.")
    
    # Initialize the SPED service
    service = SPEDService()
    
    # Process IEP documents from the input folder
    extracted_docs = service.process_iep_from_input_folder()
    
    if not extracted_docs:
        core.log("No IEP documents were processed.")
    
    core.log("~" * 80)

def test():
    """Test function for development purposes"""
    settings = get_settings()
    cnxn = aeries.get_aeries_cnxn(
        database=settings.TEST_DATABASE if settings.TEST_RUN else None,
        access_level='w'
    )
    
    service = SPEDService(cnxn)
    
    # Test getting next sequence number
    sq = service._get_next_sq(77118, 'DOC', cnxn)
    core.log(f"Next sequence for student 77118: {sq}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test()
    else:
        main()