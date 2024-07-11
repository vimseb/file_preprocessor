from os.path import basename, dirname
import os, subprocess
import shutil, zipfile, tempfile, xmltodict, json
import exifread
from PIL import Image
import xattr

#----------------------------------------------------------------------------------------------
# reuseable functions

def get_files_in_folder(folder_path):
    file_list = []
    for root, dirs, files, in os.walk(folder_path):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list

def get_dir(file):
    absolute_path = os.path.abspath(file)
    dir_path = os.path.dirname(absolute_path)
    return dir_path


#-------------------------------------------------------------------------------------------
# this is the logic to for word documents

def extract_word_meta(file):

    if file.lower().endswith((".doc", ".dot", "xls")):
        json_path = file[:-4] + ".json"
    elif file.lower().endswith((".docx", ".docm", "dotx", "dotm", "xlsx", "xlsm", "xlsb", "xltx")):
        json_path = file[:-5] + ".json"


    metadata = {}
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        extracted_items = get_files_in_folder(temp_dir)
        xml_list = []
        for i in extracted_items:
            if i.lower().endswith(".xml"):
                xml_list.append(i)
        for i in xml_list:
            with open(i, 'r', encoding='utf-8') as f:
                xml_data = f.read()
            xml_dict = xmltodict.parse(xml_data)
            metadata.update(xml_dict)
        shutil.rmtree(temp_dir, ignore_errors=True)
        with open (json_path, 'w') as json_file:
            json.dump(metadata, json_file, indent=4)
    except:
        dir_path = os.path.dirname(file)
        basename = os.path.basename(file)
        error_dict = {
                "data": "currupted or empty",
                "file": file,
                "path": dir_path,
                "basename": basename, 
                }
        with open(json_path, 'w') as json_file:
            json.dump(error_dict, json_file, indent=4)



def convert_docx_to_pdf(docx_file):
    dir_path = get_dir(docx_file)
    try:
        libreoffice_command = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir', dir_path,
                docx_file
                ]
        subprocess.run(libreoffice_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print("fail")
#------------------------------------------------------------------------------------------------

# logic for excel sheets
def convert_excel_to_pdf(file):
    dir_path = get_dir(file)
    try:
        command = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", dir_path, "--scale-to-x", "1", "--scale-to-x", "1", file]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

#-----------------------------------------------------------------------------------------------
#images logic
# also converts images to pdf's using imagemagic


def command_exists(cmd):
    try:
        # Use subprocess.call with the command and redirect output to DEVNULL
        subprocess.call([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return False
    return True

def magick_command(input_file, output):
    cmd_value = command_exists("magick")
    if cmd_value == True:
        cmd = "magick"
    else:
        cmd ="convert"
    command = [cmd, input_file, output]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def get_decimal_from_dms(dms, ref):
    degrees = dms[0].num / dms[0].den
    minutes = dms[1].num / dms[1].den / 60.0
    seconds = dms[2].num / dms[2].den / 3600.0

    decimal = degrees + minutes + seconds
    if ref == 'S' or ref == 'W':
        decimal = -decimal

    return decimal

def get_gps_coordinates(image_path):
    pathof = get_dir(image_path)
    temp_photo = f"{pathof}/tempPhoto.jpg"

    magick_command(image_path, temp_photo)


    with open(temp_photo, 'rb') as f:
        tags = exifread.process_file(f)
    
    gps_latitude = tags.get('GPS GPSLatitude')
    gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
    gps_longitude = tags.get('GPS GPSLongitude')
    gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
    
    coordinates = {}
    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = get_decimal_from_dms(gps_latitude.values, gps_latitude_ref.values)
        lon = get_decimal_from_dms(gps_longitude.values, gps_longitude_ref.values)
        coordinates['latitude'] = lat
        coordinates['longitude'] = lon
    else:
        coordinates['latitude'] = None
        coordinates['longitude'] = None
    os.remove(temp_photo)
    return coordinates


def image_meta(files):
    if files.lower().endswith((".jpg", ".png", ".gif", ".svg", "raw", "bmp")):
        json_file_path = files[:-4] + ".json"
        pdf_photo = files[:-4] + ".pdf"
    elif files.lower().endswith((".tiff", ".webp", ".heic")):
        json_file_path = files[:-5] + ".json"
        pdf_photo = files[:-5] + ".pdf"

    magick_command(files, json_file_path)
    try:
        magick_command(files, pdf_photo)
    except:
        pass

    # img_2_pdf(files, pdf_photo)

    # os.system(f"magick \"{files}\"  \"{json_file_path}\"")
    # os.system(f"magick \"{files}\" \"{pdf_photo}\"")

    coordinates = get_gps_coordinates(files)
    with open(json_file_path, 'r') as file:
        data_dict = json.load(file)
        data_dict = data_dict[0]
        data_dict.update(coordinates)
    with open(json_file_path, 'w') as file:
        json.dump(data_dict,file, indent=4)


#-----------------------------------------------------------------------------------------------
# dwg files
def get_dwg_meta(file_dwg):
    dwg_json = file_dwg[:-4] + ".json"
    os.system(f"dwgread -O JSON -o \"{dwg_json}\" \"{file_dwg}\" > NUL 2>&1")
    os.remove("NUL")
    with open(dwg_json, 'r') as file:
        data_dict = json.load(file)
    basename = os.path.basename(file_dwg)
    full_path = os.path.abspath(file_dwg)
    parent_dir = os.path.dirname(file_dwg)
    file_extension = os.path.splitext(file_dwg)[1]
    file_extension = file_extension.lstrip('.')
    data = {
            "File name": basename,
            "File path": full_path,
            "Directory": parent_dir,
            "File type": file_extension
            }
    data_dict.update(data)
    with open(dwg_json, 'w') as file:
        json.dump(data_dict, file, indent=4)


#-----------------------------------------------------------------------------------------------
#word perfect
def word_perfect_meta(file_path):
    txt_file = file_path[:-4] + ".txt"
    json_file_path = file_path[:-4] + ".json"
    os.system(f"exiftool \"{file_path}\" > \"{txt_file}\" ")
    meta_data = {}
    with open (txt_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                if line.startswith("Warning") or line.startswith("ExifTool Version"):
                    continue
                key_value = line.split(':', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    meta_data[key] = value

    attrs_dict = {}
    attrs = xattr.listxattr(file_path)
    for attr in attrs:
        value = xattr.getxattr(file_path, attr).decode('utf-8', 'ignore')
        attrs_dict[attr] = value
    meta_data.update(attrs_dict)
    with open(json_file_path, 'w') as f:
        json.dump(meta_data, f, indent=4)
    os.remove(txt_file)

#-----------------------------------------------------------------------------------------------
# Main execution
def execute(file):

    #word documents
    if file.lower().endswith(("doc", "docx", ".docm", ".dotx", "dotm")):
        convert_docx_to_pdf(file)
        extract_word_meta(file)

    # excel sheets
    if file.lower().endswith(("xlsx", "xlsm", "xls", "ods")):
        convert_docx_to_pdf(file)
        extract_word_meta(file)

    # images
    if file.lower().endswith((".jpg", ".png", "gif", ".svg", "raw", "bmp", "tiff", ".webp", ".heic")):
        try:
            image_meta(file)
        except:
            # just incase magic does not work somtimes this happens if 
            #codec is not able to read the file mostly .heic files
            json_file = file[:-5] + ".json"
            os.system(f"exiftool -a \"{file}\" > \"{json_file}\"")
    
    if file.lower().endswith(".dwg"):
        get_dwg_meta(file)

    if file.lower().endswith(".wpd"):
        word_perfect_meta(file)

        


