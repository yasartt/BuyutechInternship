import streamlit as st
import pandas as pd
import configparser
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from streamlit_utils import get_best_images,get_class_names,filter_dataframe
import configparser

st.set_page_config(
        page_title="Filter",
        page_icon="⛏️",
        layout="wide",
    )

# Cache class names to avoid reloading them unnecessarily
@st.cache_data
def load_class_names():
    return get_class_names()

# Cache best images to avoid fetching them every time the page reruns
@st.cache_data
def load_best_images(video_name):
    return get_best_images(video_name)

def create_batch():

    batch_name = "out/" + video_name + "/logs/" + "batch.pkl"
    if os.path.exists(batch_name):
        os.remove(batch_name)
    if "patch_images" in st.session_state:
        del st.session_state["patch_images"]
    
    # Get the DataFrame from the session state
    data = st.session_state["batch"]

    # Set 'wanted' to 1 only for rows where 'choose' is True
    data["wanted"] = data["choose"].apply(lambda x: 1 if x else 0)

    chosen_data = data[data["wanted"] == 1].copy()

    # Drop unnecessary columns
    chosen_data.drop(columns=["image_base64"], inplace=True)

    # Save the filtered DataFrame to a pickle file
    chosen_data.to_pickle(batch_name)

    st.session_state["batch_created"] = True

    st.session_state["preparing_mode"] = False

    st.success(f"Batch created successfully! Now you can go to the 'Label' page to start annotating.")
    
class_names = load_class_names()

if "video_name" in st.session_state:
    video_name = st.session_state["video_name"]
    
    status_path = "out/" + video_name + "/logs/logs.json"

    # Create a config parser object
    config = configparser.ConfigParser()

    # Read the config file
    config.read('config.ini')
    
    important_labels = list(map(int, config['General']['important_labels'].split(',')))


    if os.path.exists(status_path):
        best = load_best_images(video_name)
    else:
        
        message = f"The video {video_name} isn't processed."
        st.markdown(f"<p style='color:brown; font-weight:bold; font-size:17px;'>{message}</p>", unsafe_allow_html=True)
        st.stop() 
    best_df = pd.DataFrame.from_dict(best, orient='index')
    best_df['label'] = best_df['label'].apply(lambda x: class_names[int(x)])
    best_df['choose'] = False
    best_df.drop(columns=['image'],inplace=True)

    # Sort the DataFrame based on the important_labels
    best_df['is_important'] = best_df['label'].apply(lambda x: 1 if class_names.index(x) in important_labels else 0)
    best_df = best_df.sort_values(by='is_important', ascending=False).drop(columns=['is_important'])

    # "image_base64":[], "label":[], "num_samples":[], "avg_conf":[], "start" :[], "end" :[], "best":[],"best_conf":[]
    desired_order = [ 'choose','image_base64', 'label', 'num_samples', 'avg_conf', 'start', 'end', 'best', 'best_conf', 'status', 'similarity', 'hog']  # Example order
    best_df = best_df[desired_order]  # Reorder the columns
    #desired_order = ['choose', 'image_base64', 'label']
    #best_df = best_df.reindex(columns=desired_order)
    #print(best_df.head())
    #best_df = pd.DataFrame(list(best.items()), columns=['Sign', 'Occurence'])
    #st.dataframe(filter_dataframe(best_df))

    video_name = st.session_state.get("video_name", "Unknown")
    st.subheader(f"Select objects to create a batch for video: {video_name}")

    left,right = st.columns((10,1))
    with left:

        st.session_state["batch"] = st.data_editor(data = filter_dataframe(best_df), width = 1400, height=1000, column_config={
                                                        "image_base64":st.column_config.ImageColumn("Sample Image"),
                                                        "choose": st.column_config.CheckboxColumn(default=False),
                                                        "avg_conf":st.column_config.ProgressColumn(help="average confidence of this object")
                                                    }
        )
    with right:
        st.container(height = 100, border = False)
        st.button("Create batch from selected",on_click=create_batch)


