A Simple Producer/Consumer Web Link Extractor
=============================================

Interview assignment. Developed with Python 3.4.

Quick start
-----------

Run tests with:

   python tests.py

Run application with:

   python -m extr sample_input.txt

Output will go to the "extracted_links.txt" file. There are some sample data available in the 'extracted_links.txt' file.

Implementation details
----------------------

- Producer is taking urls from input files and produces markup with help from requests library
- Consumer is taking markup and extracting links
- Producer and consumer are started as two separate processes
- Communication is happening over queues
- Producer is crawling urls concurrently with threads
- Unit tests cover most of functionality