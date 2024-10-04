import streamlit as st
import os
import cv2
import copy
import subprocess
import shutil
from collections import OrderedDict
import sys
from pathlib import Path
import json
import time
from PIL import Image
from datetime import datetime
import numpy as np
sys.path.append(str(Path(__file__).resolve().parent.parent))
from streamlit_utils import collect_patches_by_frame_ids,get_class_names,get_patches


if "video_name" not in st.session_state:
    message = "Couldn't access video. Your session may have been expired. Please go back to the 'Home' page and select a video."
    st.markdown(f"<p style='color:brown; font-weight:bold; font-size:17px;'>{message}</p>", unsafe_allow_html=True)
    st.stop() 

video_name = st.session_state["video_name"]
class_names = get_class_names()

#INTERFACE
st.set_page_config(
    page_title="Labeling App",
    page_icon="🧐",
    layout="wide",
)
#callback fcns
#sidebar buttons
def sidebar_button_pressed(button_key):
    """
    callback fcn for the sidebar buttons corresponding to objects. user may select the object that he wants to label using this buttons.
    """
    st.session_state['selected_object'] = button_key
    #st.write(button_key)

def remove_label_index(label_index):
    """
    Remove all objects corresponding to the given label index from 
    patch_images_by_frame and grouped_images_by_label.
    """
    if label_index not in st.session_state['grouped_images_by_label']:
        st.warning(f"Label index {label_index} not found.")
        return
    
    # Collect unique object ids from grouped_images_by_label
    unique_object_ids = set(item["object_id"] for item in st.session_state['grouped_images_by_label'][label_index])
    excluded_count = 0
    # Remove from patch_images_by_frame
    for object_id in unique_object_ids:
        if object_id in st.session_state['patch_images']:
            excluded_count += sum(st.session_state['patch_images'][object_id]['excluded'])
            st.session_state["patch_images"].pop(int(object_id))
    
    st.session_state["selected_patch_count"] -= excluded_count

    # Remove from grouped_images_by_label
    st.session_state['grouped_images_by_label'].pop(label_index)
    
    # If the removed label index was the selected one, set selected_label_index_of_bar to the first remaining label
    if st.session_state["selected_label_index_of_bar"] == label_index:
        if st.session_state['grouped_images_by_label']:
            st.session_state["selected_label_index_of_bar"] = next(iter(st.session_state['grouped_images_by_label'].keys()))
        else:
            st.session_state["selected_label_index_of_bar"] = None

#label selection
def update_label_choice(selected_item, new_label):
    """
    depreciated
    """
    st.write(new_label)
    st.write(selected_item)
    st.session_state[selected_item]['label'] = new_label

def cancel_preparing_mode():
    """
    Method to cancel the preparing mode by setting preparing_mode to False.
    """
    st.session_state["preparing_mode"] = False

def patch_images_by_frame_checkbox_callback(frame_no, checkbox_key):
    """
    Callback function for checkboxes in the patch_images_by_frame state.
    Toggles the 'excluded' field for the corresponding image in the given frame.
    """
    current_value = st.session_state['patch_images_by_frame'][frame_no]['excluded'][checkbox_key]
    st.session_state['patch_images_by_frame'][frame_no]['excluded'][checkbox_key] = 1 if current_value == 0 else 0

def change_prepared_batch():
    """
    Update the selected_label and selected_label_index of excluded images (excluded = 1) 
    in the patch_images_by_frame session state.
    """
    if "patch_images_by_frame" not in st.session_state:
        st.warning("No patch images by frame found in session state.")
        return

    for global_id, frame_data in st.session_state["patch_images_by_frame"].items():
        for i, excluded in enumerate(frame_data["excluded"]):
            if excluded == 1:
                # Update the label and label index
                frame_data["selected_label"][i] = st.session_state['selected_label_of_page']
                frame_data["selected_label_index"][i] = st.session_state['selected_label_index_of_page']

    # Reset all checkboxes and set all excluded values to 0
    for global_id, frame_data in st.session_state["patch_images_by_frame"].items():
        for i in range(len(frame_data["excluded"])):
            frame_data["excluded"][i] = 0  # Set excluded to 0

# Function to handle the selection button click
def select_label_index(label_index):
    st.session_state["selected_label_index_of_bar"] = label_index

def prepare_batch():
    """
    Function to prepare a batch of images that are marked as excluded (excluded = 1).
    Updates the selected_label and selected_label_index of these images based on the state of the screen.
    """

    if "patch_images" not in st.session_state:
        st.warning("No patch images found in session state.")
        return

    # Initialize a set to store unique frame numbers
    unique_frame_numbers = set()
    selected_images = []

    # Iterate over patch images to update labels for excluded images
    for key, patch_data in st.session_state["patch_images"].items():
        for idx, excluded in enumerate(patch_data["excluded"]):
            if excluded == 1:
                # Update the selected_label and selected_label_index based on the current state
                patch_data["selected_label"][idx] = st.session_state['selected_label_of_page']
                patch_data["selected_label_index"][idx] = st.session_state['selected_label_index_of_page']

                unique_frame_numbers.add(patch_data["frame_no"][idx])

                # Create a selected image entry with global_id and frame_no
                selected_images.append({
                    "global_id": key,
                    "frame_no": patch_data["frame_no"][idx],
                    "selected_label": st.session_state['selected_label_of_page'],
                    "selected_label_index": st.session_state['selected_label_index_of_page']
                })
    
    st.session_state["unique_frame_numbers"] = list(unique_frame_numbers)
    # Call the method to collect patches by frame IDs
    patch_images_by_frame = collect_patches_by_frame_ids(video_name, class_names, patches_path, unique_frame_numbers)
    
    # Update patch_images_by_frame based on selected_images
    for selected_image in selected_images:
        global_id = str(selected_image["global_id"])
        frame_no = selected_image["frame_no"]
        
        if global_id in patch_images_by_frame:
            # Iterate over each image in the patch_images_by_frame entry for the global_id
            for i, frame in enumerate(patch_images_by_frame[global_id]["frame_no"]):
                if frame == frame_no:
                    # Update the label and label index
                    patch_images_by_frame[global_id]["selected_label"][i] = selected_image["selected_label"]
                    patch_images_by_frame[global_id]["selected_label_index"][i] = selected_image["selected_label_index"]
                    patch_images_by_frame[global_id]["newcomer"][i] = 0 # Distinguish the existing images from the new ones

    #st.success("Batch prepared successfully.")

    st.session_state["patch_images_by_frame"] = patch_images_by_frame

    # Selected labels of images that are already prepared
    st.session_state["selected_original_label"] = st.session_state['selected_label_of_page']

    # Set preparing_mode to True
    st.session_state["preparing_mode"] = True

def update_selected_page_info():
    """
    Updates the selected_label_of_page and selected_label_index_of_page
    according to the current selected_label_index_of_bar.
    """
    if st.session_state["selected_label_index_of_bar"] is not None:
        # Find the label data associated with the selected label index
        label_data = st.session_state['grouped_images_by_label'][st.session_state["selected_label_index_of_bar"]]
        # Update selected_label_of_page and selected_label_index_of_page
        st.session_state["selected_label_of_page"] = label_data[0]["label"]
        st.session_state["selected_label_index_of_page"] = label_data[0]["label_index"]

def choose_all_images_in_group():
    """
    Set all images in the currently selected group to excluded (excluded = 1)
    for both grouped_images_by_label and patch_images.
    """
    label_index = st.session_state["selected_label_index_of_bar"]

    if label_index not in st.session_state['grouped_images_by_label']:
        st.warning(f"Label index {label_index} not found.")
        return

    data_counter = 0
    # Iterate through all images in the selected group
    for image_data in st.session_state['grouped_images_by_label'][label_index]:
        object_id = image_data["object_id"]
        frame_no = image_data["frame_no"]
        
        # Find the corresponding entry in patch_images
        if object_id in st.session_state['patch_images']:
            patch_data = st.session_state['patch_images'][object_id]
            try:
                frame_index = patch_data['frame_no'].index(frame_no)
                
                # Set excluded = 1 in both grouped_images_by_label and patch_images
                if st.session_state['patch_images'][object_id]['excluded'][frame_index] == 0:
                    st.session_state['patch_images'][object_id]['excluded'][frame_index] = 1
                    st.session_state['grouped_images_by_label'][label_index][data_counter]['excluded'] = 1
                    st.session_state["selected_patch_count"] += 1
            except ValueError:
                st.warning(f"Frame number {frame_no} not found in patch_images for object {object_id}.")
        data_counter += 1


def unchoose_all_images_in_group():
    """
    Set all images in the currently selected group to not excluded (excluded = 0)
    for both grouped_images_by_label and patch_images.
    """
    label_index = st.session_state["selected_label_index_of_bar"]

    if label_index not in st.session_state['grouped_images_by_label']:
        st.warning(f"Label index {label_index} not found.")
        return

    data_counter = 0
    # Iterate through all images in the selected group
    for image_data in st.session_state['grouped_images_by_label'][label_index]:
        object_id = image_data["object_id"]
        frame_no = image_data["frame_no"]
        
        # Find the corresponding entry in patch_images
        if object_id in st.session_state['patch_images']:
            patch_data = st.session_state['patch_images'][object_id]
            try:
                frame_index = patch_data['frame_no'].index(frame_no)
                if st.session_state['patch_images'][object_id]['excluded'][frame_index] == 1:
                    # Set excluded = 0 in both grouped_images_by_label and patch_images
                    st.session_state['grouped_images_by_label'][label_index][data_counter]['excluded'] = 0
                    st.session_state['patch_images'][object_id]['excluded'][frame_index] = 0
                    st.session_state["selected_patch_count"] -= 1
            except ValueError:
                st.warning(f"Frame number {frame_no} not found in patch_images for object {object_id}.")
        data_counter += 1
    

def checkbox_callback(object_id, frame_no):
    """
    Callback function for the checkboxes. Toggle the 'excluded' field for both 
    `grouped_images_by_label` and `patch_images`.
    """
    for image_data in st.session_state['grouped_images_by_label'][st.session_state["selected_label_index_of_bar"]]:
        if image_data["object_id"] == object_id and image_data["frame_no"] == frame_no:
            current_value = image_data["excluded"]
            image_data["excluded"] = 1 if current_value == 0 else 0

            # Update the selected_patch_count counter
            if current_value == 0:
                st.session_state["selected_patch_count"] += 1
            else:
                st.session_state["selected_patch_count"] -= 1
            break

    # Update in patch_images (only one match expected)
    patch_data = st.session_state['patch_images'][object_id]
    frame_index = patch_data['frame_no'].index(frame_no)
    patch_data['excluded'][frame_index] = image_data["excluded"]
    
def save_data():
    """
    callback function for the save annotations button.
    upon button press, this fcn will create annotations by filtering raw annotations according to the user choices.
    downloads the annotations under out/video_name/logs/labels.
    """
    #0- create required paths and open raw annotations(all annotations)
    
    annotation_path = "./out/" + video_name + "/data/labels/annotations.json"
    frame_file_path = "./out/" + video_name + "/data/images/"
    if 'labels' not in os.listdir("./out/" + video_name + "/logs" ):
        os.mkdir("./out/" + video_name + "/logs/labels")
        os.mkdir("./out/" + video_name + "/logs/labels/images")
    label_path = ("./out/" + video_name + "/logs/labels")
    image_path = ("./out/" + video_name + "/logs/labels/images")
    yolo_txt_path = "./out/" + "batches/" + video_name  # Directory for YOLOv5 txt files
    if not os.path.exists(yolo_txt_path):
        os.makedirs(yolo_txt_path, exist_ok=True)
    
    batch_folder = os.path.join(yolo_txt_path, "labels")
    os.makedirs(batch_folder, exist_ok=True)

    batch_images_folder = os.path.join(yolo_txt_path, "images")
    os.makedirs(batch_images_folder, exist_ok=True)

    with open(annotation_path, 'r') as file:
        raw_annotations = json.load(file)

    # Collect images with excluded value 1
    selected_images = []
    for key, sub_dict in st.session_state["patch_images_by_frame"].items():
        for idx in range(len(sub_dict["image"])):
            selected_images.append({
                "key": key,
                "frame_no": sub_dict["frame_no"][idx],
                "image": sub_dict["image"][idx],
                "label": sub_dict["label"][idx],
                "label_index": sub_dict["label_index"][idx],
                "selected_label_index": sub_dict["selected_label_index"][idx],
                "conf": sub_dict["conf"][idx],
                "selected_label": sub_dict["selected_label"][idx],
                "bbox": sub_dict["bbox"][idx],
            })

    #1- remove unwanted tracks(checked ones) from st.session_state["patch_images"] 
        #also remove the excluded objects from tracks
    #images = copy.deepcopy(st.session_state["patch_images"])
    
    #images = {k: v for k, v in st.session_state["patch_images"].items() if v["wanted"] != 0}
        
    
    #2- copy the images that contains the selected tracks to the /labels/images 
    #find the images that contains objects from selected tracks
    #frames = []
    #for key in images.keys():
        #st.write(images[key])
    #    for frame_no in images[key]["frame_no"]:
    #        frames.append(int(frame_no))
    #frames = list(OrderedDict.fromkeys(frames))
    #st.write(frames)
    #iterate over raw frames, copy to the labels/images if its in the list(frames)
    #for ann in raw_annotations["images"]:
    #    if int(ann["id"]) in frames:
    #        source = ann["file_name"]
    #        destination = image_path + "/" + ann["file_name"].split("/")[-1]
    #       shutil.copy(source, destination)

    #3-copy the annotations that contains the selected tracks to /labels/annotations.json. Also update the label if required
    #annotations = {"annotations":[],"images":[],"categories":[]}
    #for ann in raw_annotations["annotations"]:
    #    if int(ann["image_id"]) in frames:
    #        id = int(ann["global_id"])
    #        if id in images:
    #            new_label = images[id]["selected_label_index"][0]
    #            ann["category_id"] = new_label
    #        annotations["annotations"].append(ann)

    #3-copy the image annotations to the /labels/annotations.json
    #for ann in raw_annotations["images"]:
    #    if int(ann["id"]) in frames:
    #        destination = image_path + "/" + ann["file_name"].split("/")[-1]
    #        ann["file_name"] = destination
    #        annotations["images"].append(ann)
    #
    #with open(os.path.join(label_path, 'annotations.json'), 'w') as f:
    #        json.dump(annotations, f, indent=4)
    
    for img in selected_images:

        for image_info in raw_annotations["images"]:
            if image_info["id"] == img["frame_no"]:
                img["img_width"] = image_info["width"]
                img["img_height"] = image_info["height"]
                break  # Exit the loop once the image dimensions are found

    # Creating YOLOv5 text files with logic for updating labels if coordinates match
    for img in selected_images:
        yolo_file = os.path.join(batch_folder, f"{img['frame_no']}.txt")

        existing_lines = []
        updated_lines = []

        # Check if the file already exists
        if os.path.exists(yolo_file):
            # Open the file and read all existing lines
            with open(yolo_file, 'r') as f:
                existing_lines = f.readlines()  # Read all lines into a list

        # Prepare the new entry (line)
        if "bbox" in img and img["bbox"]:  # Check if bbox exists
            x1, y1 = img["bbox"][0]
            x2, y2 = img["bbox"][1]
            x_center = (x1 + x2) / 2.0 / img["img_width"]
            y_center = (y1 + y2) / 2.0 / img["img_height"]
            width = (x2 - x1) / img["img_width"]
            height = (y2 - y1) / img["img_height"]
            new_line = f"{img['selected_label_index']} {x_center} {y_center} {width} {height}\n"
        else:
            # Using placeholder values for bounding boxes (0, 0, 0, 0)
            new_line = f"{img['selected_label_index']} 0.0 0.0 0.0 0.0\n"

        # Parse existing lines and check for matching coordinates
        line_found = False
        for line in existing_lines:
            parts = line.strip().split()
            existing_class_id = int(parts[0])
            existing_x_center, existing_y_center, existing_width, existing_height = map(float, parts[1:])

            # Check if coordinates match
            if (existing_x_center == x_center and existing_y_center == y_center and
                existing_width == width and existing_height == height):
                line_found = True
                # If coordinates match but labels differ, replace the line with the new one
                if existing_class_id != img['selected_label_index']:
                    updated_lines.append(new_line)
                else:
                    updated_lines.append(line)  # Keep the existing line if the label matches
            else:
                updated_lines.append(line)  # Keep non-matching lines

        # If no matching coordinates were found, append the new line
        if not line_found:
            updated_lines.append(new_line)

        # Write the updated lines back to the file
        with open(yolo_file, 'w') as f:
            f.writelines(updated_lines)


    # 6- Copy images to the batch_images_folder
    for frame_no in st.session_state["unique_frame_numbers"]:
    # Construct the source and destination paths for the JPEG file
        source_image_path = os.path.join(frame_file_path, f"{frame_no}.jpeg")
        destination_image_path = os.path.join(batch_images_folder, f"{frame_no}.jpeg")

        # Check if the file already exists at the destination
        if not os.path.exists(destination_image_path):
            # Copy the file to the destination folder
            shutil.copy(source_image_path, destination_image_path)


    #4-update the status data on logs.json. This file is used to monitor which tracks are labeled
    #status_path = "out/" + video_name + "/logs/logs.json"
    #with open(status_path, 'r') as file:
    #    # Parse the JSON file
    #    status = json.load(file)
    #    labeled = list(images.keys())
    #    for key in list(status.keys()):
    #        #st.write(key)
    #        if int(key) in labeled:
    #            status[key] = 0

    #with open(status_path, 'w') as f:
    #    json.dump(status, f, indent=4) 

    # Set preparing_mode to False
    st.session_state["preparing_mode"] = False

    st.session_state['selected_patch_count'] = 0

    # Reset all excluded values to 0
    for key, patch_data in st.session_state["patch_images"].items():
        for idx in range(len(patch_data["excluded"])):
            patch_data["excluded"][idx] = 0

    # Reset all excluded values to 0 in grouped_images_by_label
    for label_index, label_data in st.session_state['grouped_images_by_label'].items():
        for image_data in label_data:
            image_data["excluded"] = 0

    # Display success message after saving
    st.success("Annotations have been saved successfully!")
    

# Define patches_path and check if it exists
patches_path = f"out/{video_name}/logs/patches/"
if not os.path.exists(patches_path):
    message = "Couldn't find patches. Please check the path or the batch processing."
    st.markdown(f"<p style='color:brown; font-weight:bold; font-size:17px;'>{message}</p>", unsafe_allow_html=True)
    st.stop()    

# Initialize preparing_mode in the session state
if "preparing_mode" not in st.session_state:
    st.session_state["preparing_mode"] = False
# Initialize session state
if "selected_patch_count" not in st.session_state:
    st.session_state["selected_patch_count"] = 0
#initialize 
if "patch_exists" not in st.session_state:
    st.session_state["patch_exists"] = False
if "checkbox_status" not in st.session_state:
    st.session_state["checkbox_status"] = {"id":0}
if "unique_frame_numbers" not in st.session_state:
    st.session_state["unique_frame_numbers"] = []
if "patch_images_by_frame" not in st.session_state:
    st.session_state['patch_images_by_frame'] = {}  # Initialize as an empty dictionary
if 'grouped_images_by_label' not in st.session_state:
    st.session_state['grouped_images_by_label'] = {}
if "patch_images" not in st.session_state:
    st.session_state['patch_images'] = {}  # Initialize as an empty dictionary

    # Load patch images if batch exists
    batch_name = "out/" + video_name + "/logs/" + "batch.pkl"
    if os.path.exists(batch_name):
        patch_images = get_patches(video_name, class_names, patches_path)
        # Group the patch images by label 
        if len(patch_images) > 0:
            st.session_state['patch_images'] = patch_images
            grouped_images_by_label = {}

            # Iterate through the patch images and group them by label_index
            for object_id, data in st.session_state['patch_images'].items():
                for idx, label_index in enumerate(data['label_index']):
                    if label_index not in grouped_images_by_label:
                        grouped_images_by_label[label_index] = []
                    
                    grouped_images_by_label[label_index].append({
                        "image": data["image"][idx],
                        "frame_no": data["frame_no"][idx],
                        "label": data["label"][idx],
                        "label_index": label_index,
                        "selected_label": data["selected_label"][idx],
                        "selected_label_index": data["selected_label_index"][idx],
                        "conf": data["conf"][idx],
                        "wanted": data["wanted"][idx],
                        "excluded": data["excluded"][idx],
                        "object_id": object_id
                    })

            st.session_state['grouped_images_by_label'] = grouped_images_by_label
            st.session_state['patch_exists'] = True
            st.session_state['selected_patch_count'] = 0
    else:
        st.session_state['patch_exists'] = False

# Ensure 'wanted' field is initialized for all images
for key in st.session_state['patch_images'].keys():
    if "wanted" not in st.session_state['patch_images'][key]:
        st.session_state['patch_images'][key]["wanted"] = 0  # Initialize wanted field for each object

# Initialize the array for selected patches
if "selected_patches" not in st.session_state:
    st.session_state["selected_patches"] = []

if 'selected_original_label' not in st.session_state:
    st.session_state['selected_original_label'] = []

# Initialize session state for selected_label_index_of_bar
if "selected_label_index_of_bar" not in st.session_state:
    st.session_state["selected_label_index_of_bar"] = None

if st.session_state['patch_exists'] and len(st.session_state['patch_images']) > 0 and len(st.session_state['grouped_images_by_label']) > 0 and st.session_state['batch_created']:

    if not st.session_state["preparing_mode"]:
            
        if "selected_label_index_of_bar" not in st.session_state or st.session_state["selected_label_index_of_bar"] is None:
            st.session_state["selected_label_index_of_bar"] = next(iter(st.session_state['grouped_images_by_label'].keys()))
            update_selected_page_info()
        # Display the sidebar with label_index instead of object IDs
        with st.sidebar:
            st.write("Select a label index to manage its images")

            # Iterate over grouped label indices and display a row for each index
            for label_index, label_data in st.session_state['grouped_images_by_label'].items():
                scol1, scol2, scol3 = st.columns([4, 2, 2])

                with scol1:
                    # Button to set the selected_label_index_of_bar
                    if st.button(label_data[0]["label"], key=f"select_{label_index}", use_container_width=True, on_click=select_label_index, args=(label_index,)):
                        pass  # Action is handled in the on_click argument

                with scol2:
                    # Display the first image in the group
                    st.image(label_data[0]["image"], channels='BGR')

                with scol3:
                    # Remove button to remove all images under the label index
                    st.button("❌", key=f"remove_{label_index}", on_click=remove_label_index, args=(label_index,))
                               
        # Get the sorted keys
        #sorted_keys = sorted(st.session_state['patch_images'].keys())

        # SLIDE BAR (LEFT)
        #for key in sorted_keys:
        #    scol1, scol2, scol3 , scol4 = st.sidebar.columns([2,1,3,1])
        #    with scol1:
        #        pass
        #        if st.button(str(key),use_container_width=True):
        #            sidebar_button_pressed(key)
        #    with scol2:
        #        st.image(st.session_state['patch_images'][key]['image'][0],channels = 'BGR')
        #    with scol3:
        #        label_index = st.session_state['patch_images'][key]['selected_label'][0]
        #        st.markdown(label_index)
        #    with scol4:
        #        keyvalue = "remove_" + str(key)
        #        if st.button("❌", key=keyvalue):
        #            # Remove the corresponding row
        #            # Count excluded images for the key before removing
        #            excluded_images_count = sum(st.session_state['patch_images'][key]['excluded'])

                    # Decrease the counter by the number of excluded images
        #            st.session_state['selected_patch_count'] -= excluded_images_count
                    
                    # Check if the key being removed is the selected_object
        #            if key == st.session_state['selected_object']:
                        # Pop the key from patch_images
         #               st.session_state["patch_images"].pop(int(key))
                        
                        # Check if there are still objects left
        #                if st.session_state["patch_images"]:
                            # Assign the first object found as the new selected_object
        #                    st.session_state['selected_object'] = list(st.session_state['patch_images'].keys())[0]
        #                else:
        #                    st.session_state['selected_object'] = None  # Or handle it as per your app's requirement (e.g., stopping or warning)

        #            else:
                        # Just pop the key if it's not the selected_object
        #                st.session_state["patch_images"].pop(int(key))
                    
        #            st.rerun()
    

    #MAIN PAGE(RIGHT)
    if not st.session_state["preparing_mode"] and st.session_state["selected_label_index_of_bar"] is not None:
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info("Please choose patches that you want to assign the same label to in 1 preparation.")

            st.header("Choose patches to prepare a batch")
            if class_names and st.session_state["selected_label_index_of_bar"] is not None:
                label_name = class_names[st.session_state["selected_label_index_of_bar"]]
                st.subheader(f"Label: {label_name}")

            if st.session_state["selected_label_index_of_bar"] in st.session_state['grouped_images_by_label']:
                grouped_images = st.session_state['grouped_images_by_label'][st.session_state["selected_label_index_of_bar"]]

                with st.expander(label="Detections", expanded=True):
                    button_col1, button_col2, _ = st.columns([1, 2, 2])  # Adjust the width ratio as needed
    
                    with button_col1:
                        st.button("Choose all", on_click=choose_all_images_in_group)
                    
                    with button_col2:
                        st.button("Unchoose all", on_click=unchoose_all_images_in_group)
                    
                    num_columns = 5
                    columns = st.columns(num_columns)

                    for i, image_data in enumerate(grouped_images):
                        col = columns[i % num_columns]
                        col.image(image_data["image"], caption=f"Frame {image_data['frame_no']}", channels='BGR')
                        
                        # Use excluded status from grouped_images_by_label
                        current_value = image_data["excluded"]

                        col.checkbox(
                            label=f"Checkbox {i}",
                            key=f"{image_data['object_id']}_{image_data['frame_no']}",
                            value=current_value == 1,
                            on_change=checkbox_callback,
                            args=(image_data['object_id'], image_data['frame_no']),
                            label_visibility="collapsed"  # Hide the label if you don't want it to be visible
                        )

        with col2:
            # Existing code for displaying the selected label and handling batch preparation
            sorted_class_names = sorted(class_names)
            selected_label = st.session_state['selected_label_of_page']

            selected_label_index = sorted_class_names.index(selected_label)

            selected_label = st.selectbox(
                label='Label',
                options=sorted_class_names,
                index=selected_label_index
            )
            
            st.session_state['selected_label_of_page'] = selected_label
            for i, c in enumerate(class_names):
                if c == selected_label:
                    st.session_state['selected_label_index_of_page'] = i
                    
            st.button(label="Prepare", on_click=prepare_batch, disabled=st.session_state["selected_patch_count"] == 0)
            st.write(f"Number of selected patches: {st.session_state['selected_patch_count']}")

            num_columns = 5  # Adjust the number of columns based on how many images you want in a row
            excluded_columns = st.columns(num_columns)
            excluded_images = []
            # Collect and display excluded images
            for key, patch_data in st.session_state["patch_images"].items():
                for idx, excluded in enumerate(patch_data["excluded"]):
                    if excluded == 1:
                        excluded_images.append(patch_data["image"][idx])
            
            # Display images in columns
            for i, image in enumerate(excluded_images):
                col = excluded_columns[i % num_columns]
                col.image(image, caption=f"", channels='BGR', use_column_width=True)

            
    else:
        col1, col2 = st.columns([2, 1])
        with col1:

            # Display excluded images at the top
            if "patch_images" in st.session_state:
                st.subheader("Selected Images (Labeled as {})".format(st.session_state['selected_original_label']))
                num_columns = 10
                excluded_columns = st.columns(num_columns)
                excluded_images = []

                for key, patch_data in st.session_state["patch_images"].items():
                    for idx, excluded in enumerate(patch_data["excluded"]):
                        if excluded == 1:
                            excluded_images.append(patch_data["image"][idx])

                for i, image in enumerate(excluded_images):
                    col = excluded_columns[i % num_columns]
                    col.image(image, caption=f"", channels='BGR', use_column_width=True)

            newcomers_exist = any(
                1 in data["newcomer"] for data in st.session_state["patch_images_by_frame"].values()
            )

            if newcomers_exist:
                st.markdown("---")
                st.subheader("Other Images That Will Be Saved")
                
                sorted_class_names = sorted(class_names)  # Sort the class names
                selected_label = st.session_state['selected_label_of_page']

                # Find the index of the selected label in the sorted class names
                selected_label_index = sorted_class_names.index(selected_label)

                # Create the selectbox with the correct initial value
                selected_label = st.selectbox(
                    label='Label',
                    options=sorted_class_names,
                    index=selected_label_index
                )
                st.session_state['selected_label_of_page'] = selected_label

                for i,c in enumerate(class_names):
                    if c == selected_label:
                        st.session_state['selected_label_index_of_page'] = i
                st.button(label = "Change Label", on_click=change_prepared_batch)

                # Get the unique labels from the patch_images_by_frame
                unique_labels = set()
                for data in st.session_state["patch_images_by_frame"].values():
                    for i, image_label in enumerate(data["selected_label"]):
                        if data["newcomer"][i] == 1:
                            unique_labels.add(image_label)

                # Iterate over the unique labels and display images grouped by these labels
                for label in unique_labels:
                    st.markdown(f"**Label: {label}**")
                    num_columns = 5
                    columns = st.columns(num_columns)
                    col_idx = 0

                    # Iterate over patch_images_by_frame to find and display images with the current label
                    for global_id, data in st.session_state["patch_images_by_frame"].items():
                        for i, image_label in enumerate(data["selected_label"]):
                            if image_label == label and data["newcomer"][i] == 1:
                                col = columns[col_idx % num_columns]
                                # Ensure the key is unique by combining label, global_id, and index
                                checkbox_key = f"label_{label}_global_{global_id}_image_{i}"
                                col.image(data["image"][i], caption=f"Frame {data['frame_no'][i]}", channels='BGR')
                                col.checkbox(
                                    label=f"Checkbox {i}",  # Provide a meaningful label here
                                    key=checkbox_key,
                                    value=data["excluded"][i] == 1,
                                    on_change=patch_images_by_frame_checkbox_callback,
                                    args=(global_id, i),
                                    label_visibility="collapsed"  # Hide the label if you don't want it to be visible
                                )

                                col_idx += 1
        with col2:

            #st.markdown("---")
            # Button to save the data
            if st.button("Save Annotations", on_click=save_data):
                pass

            # Cancel button
            st.button("Cancel", on_click=cancel_preparing_mode)

else:
    #if the data is not filtered, display a warning message to the user
    #st.write("Batch created: ", st.session_state.get("batch_created", False))
    #st.write("Patch exists: ", st.session_state.get("patch_exists", False))
    #st.write("Grouped images by label: ", st.session_state.get("grouped_images_by_label", False))
    #st.write("Patch images: ", st.session_state.get("patch_images", False))
    message = "Please go to the 'Filter' page and filter the data first"
    st.markdown(f"<p style='color:brown; font-weight:bold; font-size:17px;'>{message}</p>", unsafe_allow_html=True)


#st.snow()