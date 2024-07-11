import fileFunctions, sys
from tqdm import tqdm


def change_extenstion_to_pdf(file):
    if file.lower().endswith((".doc", ".dot", "xls", "wpd", "jpg", "png", "gif", "svg", "raw", "bmp", "xls" )):
        file = file[:-4] + ".pdf"
    else:
        file = file[:-5] + "pdf"
    return file

def remove_extra(file_list):
    for file in file_list:
        if file.lower().endswith(".pdf"):
            pass
        else:
            string_to_remove = change_extenstion_to_pdf(file)
            if string_to_remove in file_list:
                file_list.remove(string_to_remove)
    return file_list


if __name__ == "__main__":
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)
    

    file_list = fileFunctions.get_files_in_folder(folder_path)
    file_list = remove_extra(file_list)
    print("Extracting metadata..")
    for i in tqdm(file_list):
        fileFunctions.execute(i)



