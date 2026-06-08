import ebooklib
from ebooklib import epub
import os
import tempfile

def extract_images_epub(epub_path, output_dir=None):
    
    book = epub.read_epub(epub_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
    
    if not items:
        return [], None
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="epub_images_")
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    images_paths = []
    
    for item in items:
        fileName = os.path.basename(item.file_name)
        output_path = os.path.join(output_dir, fileName)
        
        with open(output_path, 'wb') as f:
            f.write(item.get_content())
            
        images_paths.append(output_path)
    return images_paths, output_dir