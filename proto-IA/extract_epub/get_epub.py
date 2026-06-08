import zipfile
import os
import tempfile 
from lxml import etree

# def extract_images_from_epub(epub_path):
# # Ouvrir le fichier EPUB comme une archive ZIP
#     os.makedirs('images', exist_ok=True)
#     with zipfile.ZipFile(epub_path) as z:
#       for images in z.namelist():
#         if images.endswith(".jpg"):
#           print(images)
#           z.extract(images, 'images')
      

# # Extraire les images dans le EPUB, et les enregistrer dans un dossier local "images"
epub_file = "C:/Users/adminpaon/Downloads/abbot_flatland.epub"
# extract_images_from_epub(epub_file)


def extract(epub):
  
  os.makedirs('test', exist_ok=True)
  with zipfile.ZipFile(epub, 'r') as z:
    z.extractall('test')
  
  containerFilePath = "test/META-INF/container.xml"
  tree = etree.parse(containerFilePath)
  
  for rootFilePath in tree.xpath("//*[local-name()='container']"
                                        "/*[local-name()='rootfiles']"
                                        "/*[local-name()='rootfile']"
                                        "/@full-path"):
    
    contentFilePath = f"{containerFilePath}/{rootFilePath}"
    contentFileDirPath = os.path.dirname(contentFilePath)
    
    