import zipfile
import xml.etree.ElementTree as ET
import sys

docx_path = r'd:\SIH PS2\AERIS_Full_Project_Documentation.docx'

try:
    z = zipfile.ZipFile(docx_path)
    tree = ET.parse(z.open('word/document.xml'))
    root = tree.getroot()
    
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    paragraphs = []
    for para in root.iter(ns + 'p'):
        texts = []
        for t in para.iter(ns + 't'):
            if t.text:
                texts.append(t.text)
        if texts:
            paragraphs.append(''.join(texts))
    
    with open(r'd:\SIH PS2\extracted_docx.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(paragraphs))
    
    print("Extraction successful!")
    print(f"Total paragraphs: {len(paragraphs)}")
except Exception as e:
    print(f"Error: {e}")
