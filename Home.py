import streamlit as st
import configparser
import json
import os
import pandas as pd
import random
from datetime import datetime
from streamlit_utils import get_best_images,get_class_names,get_quotes,create_video_info
from preview_utils import preview_video

#whenever new video is selected, delete the data from previous one
def new_video():
    if "patch_images" in st.session_state:
        del st.session_state["patch_images"]
        st.session_state["patch_exists"] = False
        st.session_state["batch_created"] = False

def get_random_quote():
    quotes,cuma = get_quotes()
    now = datetime.now()
    # Check if the current day is Friday
    is_friday = now.weekday() == 4 
    if is_friday:  
        quote = random.choice(cuma)
    else:
        quote = random.choice(quotes)
    return quote

def file_selector(folder_path='./out'):
    filenames = os.listdir(folder_path)
    if "video_name" in st.session_state and st.session_state["video_name"] in filenames:
        default_index = filenames.index(st.session_state["video_name"])
    else:
        default_index = 0  # Default to the first file if no match is found

    selected_filename = st.selectbox('Select a video', filenames, index=default_index, on_change=new_video)
    return os.path.join(folder_path, selected_filename)

st.set_page_config(
    page_title="Labeling App",
    page_icon="🇹🇷",
    layout="wide",
)
if "batch" not in st.session_state:
    st.session_state["batch"] = None
if "create" not in st.session_state:
    st.session_state["create"] = None
if "batch_created" not in st.session_state:
    st.session_state["batch_created"] = False

def main():
    class_names = get_class_names()
    st.title("Home")

    left,seperator,center,right = st.columns([4,1,3,1])
    with left:
        videos = create_video_info()
        st.dataframe(videos, width=800)
        with st.expander("Preview"):
            st.write("run preview.py")
            st.write("Example: python preview.py 010380F.MP4 4")
        with st.expander("Process"):
            st.write("run autolabel_fast.py using the settings on config.ini")


    with center:
        file_name = file_selector()
        st.session_state["video_name"] = file_name.split("/")[-1]
        # name = "Name of the video: " + st.session_state["video_name"]
        # st.markdown(f"<p style='color:black; font-weight:bold; font-size:25px;'>{name}</p>", unsafe_allow_html=True)
        # detections = "Objects detected in the video: "
        # st.markdown(f"<p style='color:black; font-size:20px;'>{detections}</p>", unsafe_allow_html=True)

        #read preview.json to access detection and class distribution info
        info = pd.DataFrame(columns=['Name','Count','Current'])
        file_path = file_name + "/preview.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                preview = json.load(file)
            for key in preview.keys():
                count = len(preview[key]['frame_no'])
                current = preview[key]['current']
                status = int(preview[key]['status'])
                temp_df = pd.DataFrame({'Name':[key], 'Count':[count], 'Importance':[status], 'Current':[current]})
                info = pd.concat([info, temp_df], ignore_index=True)
            st.dataframe(info)
        else: 
            st.write("Video preview is not available")
        #:x:
        #:heavy_check_mark:rr
        #:red_circle:
        #:large_green_circle:
    

    with right:
        st.container(height = 600, border = False)
        message = get_random_quote()
        st.markdown(f"<p style='color:green; font-weight:bold; font-size:17px;'>{message}</p>", unsafe_allow_html=True)
        #if st.session_state["batch"] is not None:
        #    st.write(st.session_state["batch"]["choose"])

        
if __name__ == "__main__":
    main()