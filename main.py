import io

import streamlit as st
import boto3
import uuid
import json
import pandas as pd
import qrcode
import cv2
import zxingcpp as zx
import numpy as np
import requests


def get_upcs(categories):
    upcs = {}
    for category, data in categories.items():
        for food, fooddata in data.items():
            if len(fooddata) > 2:
                if fooddata[2]:
                    upcs[fooddata[2]] = [category, food]
            else:
                categories[category][food].append(None)
    return upcs


def setup_session_state(name, startval):
    if name not in st.session_state:
        st.session_state[name] = startval


def r2_key(fid):
    return f"freezer {fid}"


def r2_exists(key):
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except:
        return False


def update_s3(data):
    categories = data
    fmeta["items"] = categories
    s3.put_object(Bucket=BUCKET,
                  Key=r2_key(fid),
                  Body=json.dumps(fmeta))


s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{st.secrets['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=st.secrets["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

BUCKET = st.secrets["R2_BUCKET"]
BASE_URL = "freezerone.streamlit.app"  #replace later!!!
# setup_session_state("page", "home")

setup_session_state("tab_state", "Add Food")


def go_to_add():
    st.session_state.go_to_add = True


def go_to_use():
    st.session_state.go_to_use = True


def better_title(text):
    titled_text = str(text).title()
    result = []

    for i, char in enumerate(titled_text):
        if i > 0 and titled_text[i - 1] == "'" and titled_text[i - 2:i - 1].isalpha():
            result.append(char.lower())
        else:
            result.append(char)

    return "".join(result)

def tab_change():
    # st.write("Tab State:", st.session_state.tab_state)
    # st.write("Tab Navigation:", st.session_state.tab_navigation)
    temp = st.empty()
    temp.write(st.session_state.get("tab_state"))
    temp.empty()


def handle_action():
    click = st.session_state[f"action_click"]
    df = st.session_state.df
    if "View on Add Page" in click["label"]:
        # st.session_state.add_clicked_row = click
        # st.session_state.add_page_start = True
        # st.session_state.use_page_start = False
        st.session_state.tab_navigation = "Add Food"
    elif "View on Use Page" in click["label"]:
        # st.session_state.add_page_start = False
        # st.session_state.use_page_start = True
        st.session_state.tab_navigation = "Use Food"
    st.session_state.page_category = df["Categories"][click["row"]]
    st.session_state.page_food = df["Food"][click["row"]]
    temp = st.empty()
    temp.write(st.session_state.get("tab_navigation"))
    temp.empty()


def handle_action_for_creator(catindex):
    click = st.session_state[f"action_click{catindex}"]
    df = st.session_state.get(f"df{catindex}")
    if "View on Add Page" in click["label"]:
        # st.session_state.add_clicked_row = click
        # st.session_state.add_page_start = True
        # st.session_state.use_page_start = False
        st.session_state.tab_navigation = "Add Food"
    elif "View on Use Page" in click["label"]:
        # st.session_state.add_page_start = False
        # st.session_state.use_page_start = True
        st.session_state.tab_navigation = "Use Food"
    st.session_state.page_category = [*categories][catindex]
    st.session_state.page_food = df["Food"][click["row"]]
    temp = st.empty()
    temp.write(st.session_state.get("tab_navigation"))
    temp.empty()
    # st.stop()


st.title("FreezerOne")
st.subheader("What's in your freezer?")
temp2 = st.empty()

if not "fid" in st.query_params:
    st.subheader("Welcome to FreezerOne")
    hometabs = st.tabs(["Register a Freezer", "Open Freezer Menu", "How"])
    with hometabs[0]:
        st.write("Hello!")
        st.write("Here you can register a Freezer.")
        name = st.text_input("What is your Freezer's name?")
        if st.button("Create!", type="primary"):
            fid = uuid.uuid4().hex[:6]
            cid = uuid.uuid4().hex[:6]
            st.session_state["page"] = "creator"
            meta = {"name": name,
                    "fid": fid,
                    "cid": cid,
                    "items": {}}
            s3.put_object(Bucket=BUCKET,
                          Key=r2_key(fid),
                          Body=json.dumps(meta),
                          )
            st.query_params["fid"] = fid
            st.query_params["cid"] = cid
            st.session_state.totoast = "Freezer created!"
            st.session_state.totoastemoji = ":material/task_alt:"
            st.rerun()
    with hometabs[1]:
        st.write("Hello!")
        st.write("Here you can go back to your Freezer Creator or Freezer Guest page.")
        gobackfile = st.file_uploader("Upload your Recover file", type="json")
        if gobackfile:
            file = json.load(gobackfile)
            try:
                if file["access"] in ["creator", "admin"]:
                    st.query_params["cid"] = file["cid"]
                st.query_params["fid"] = file["fid"]
                st.rerun()
            except Exception as e:
                st.error("Invalid file uploaded!")
                # e
                # file
    with hometabs[2]:
        # st.markdown("""
        # ### Welcome to FreezerOne!
        #
        # Here is some information on how to use this site.
        #
        # 1. **Home Page**
        #     a. **Register a Freezer**
        #         - Type in the name of your Freezer and press Create.
        #         - You will be redirected to your new Freezer's Creator Page.
        #     b. **Open Freezer Menu**
        #         - Use this to go to a Freezer Creator or Freezer Guest page that was already created.
        #         - Upload your Freezer Creator or Freezer Guest Recover file.
        #         - You will be redirected to your Freezer Creator or Freezer Guest Page.
        #         - *If it doesn't work, delete the uploaded file and try again.*
        #
        # 2. **Creator Page**
        #     - *This page is mostly used for deleting foods and printing the QR codes.*
        #     a. **Add Categories**
        #         - To add a category, go to the "Add Categories" tab, type in the name of the category, and click "Add Category".
        #     b. **Add Food**
        #         - To add food, go to the "Add Food" tab, select the category or type in a new one.
        #         - Select a previously used food or type in a new food.
        #         - Type in the quantity of food you're adding
        #         - If you're adding a new food, type in the unit of measurement you will be using.""")
        # st.subheader("Welcome to FreezerOne")
        st.write("Here is some information on how to use this site.")
        with st.expander("**Home Page**"):
            with st.expander("**Register a Freezer**", type="compact"):
                st.markdown("""
                - Type in the name of your Freezer and press Create.
                - You will be redirected to your new Freezer's Creator Page.""")
            with st.expander("**Open Freezer Menu**", type="compact"):
                st.markdown("""
                - Use this to go to a Freezer Creator or Freezer Guest page that was already created.
                - Upload your Freezer Creator or Freezer Guest Recover file.
                - You will be redirected to your Freezer Creator or Freezer Guest Page.
                - *If it doesn't work, click the "x" on the uploaded file and try again.*""")
        with st.expander("**Guest Page**"):
            st.markdown("""
            *This page is where you go when you scan the QR code*""")
            with st.expander("**Add Food**", type="compact"):
                st.markdown("""
                - Select the category or type in a new one.
                - Select a food or type in a new food.
                - Type in the quantity of food you're adding.
                - If you're adding a new food, type in the unit of measurement you will be using.
                - Click "Add Food!" to add the food.""")
            with st.expander("**Use Food**", type="compact"):
                st.markdown("""
                - Select the category of the food you're using.
                - Select the food.
                - Type in the quantity of food you're adding.
                - Click "Use Food!" to use the food.""")
            with st.expander("**View Inventory**", type="compact"):
                st.markdown("""
                    - Look at what food you have.
                    - If you're looking to add or use food that you already entered in FreezerOne and you forgot what section it's in...
                        - Find it on the View Inventory page.
                        - Click the three dots.
                        - Click "View on Add Page" or "View on Use Page" depending on what you want to do.""")
            with st.expander("**Scan Barcode**", type="compact"):
                st.markdown("""
                    - If your food has a barcode on it...
                        - Select one of the tabs.
                            - There are two camera tabs because some devices don't work on both tabs.
                            - If one of them doesn't work, try the other tab. If neither of them work, go to "Manual Entry".
                        - Take a photo of the barcode or type in the entire number shown on the barcode, including the numbers on the side.
                        - If the barcode isn't linked with a food...
                            - You can add that food by going to the "Add Food from Barcode" tab and select the category or type in a new one.
                            - You can link it to a food by going to the "Assign Barcode to Food" and selecting the food.
                                - This makes it so that when you use the barcode, it will show up as the food you linked to it.
                        - If the barcode is linked with a food...
                            - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
                            - Click "Unlink with Food" to remove the barcode from the food.""")

            # st.markdown("""
            # *This page is where you go when you scan the QR code* 
            # 
            # **Add Food**
            # - Select the category or type in a new one.
            # - Select a food or type in a new food.
            # - Type in the quantity of food you're adding.
            # - If you're adding a new food, type in the unit of measurement you will be using.
            # - Click "Add Food!" to add the food.
            # 
            # **Use Food**
            # - Select the category of the food you're using.
            # - Select the food.
            # - Type in the quantity of food you're adding.
            # - Click "Use Food!" to use the food.
            # 
            # **View Inventory**
            # - Look at what food you have.
            # - If you're looking to add or use food that you already entered in FreezerOne and you forgot what section it's in...
            #     - Find it on the View Inventory page.
            #     - Click the three dots.
            #     - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
            # 
            # **Scan Barcode**
            # - If your food has a barcode on it...
            #     - Select one of the tabs.
            #         - There are two camera tabs because some devices don't work on both tabs.
            #         - If one of them doesn't work, try the other tab. If neither of them work, go to "Manual Entry".
            #     - Take a photo of the barcode or type in the entire number shown on the barcode, including the numbers on the side.
            #     - If the barcode isn't linked with a food...
            #         - You can add that food by going to the "Add Food from Barcode" tab and select the category or type in a new one.
            #         - You can link it to a food by going to the "Assign Barcode to Food" and selecting the food.
            #             - This makes it so that when you use the barcode, it will show up as the food you linked to it.
            #     - If the barcode is linked with a food...
            #         - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
            #         - Click "Unlink with Food" to remove the barcode from the food.
            # """)
        with st.expander("**Creator Page**"):
            with st.expander("**Add Food**", type="compact"):
                st.markdown("""
                    - Select the category or type in a new one.
                    - Select a food or type in a new food.
                    - Type in the quantity of food you're adding.
                    - If you're adding a new food, type in the unit of measurement you will be using.
                    - Click "Add Food!" to add the food.""")
            with st.expander("**Use Food**", type="compact"):
                st.markdown("""
                    - Select the category of the food you're using.
                    - Select the food.
                    - Type in the quantity of food you're adding.
                    - Click "Use Food!" to use the food.""")
            with st.expander("**Edit Inventory**", type="compact"):
                st.markdown("""
                    - Look at what food you have.
                    - Edit anything about the food, including the unit of measurement, the name, and the amount.
                        - You can also delete foods entirely by selecting the row on the left-hand side and pressing the trash can icon.
                    - If you're looking to add or use food that you already entered in FreezerOne and you forgot what section it's in...
                        - Find it on the Edit Inventory page.
                        - Click the three dots.
                        - Click "View on Add Page" or "View on Use Page" depending on what you want to do.""")
            with st.expander("**Scan Barcode**", type="compact"):
                st.markdown("""
                    - If your food has a barcode on it...
                        - Select one of the tabs.
                            - There are two camera tabs because some devices don't work on both tabs.
                            - If one of them doesn't work, try the other tab. If neither of them work, go to "Manual Entry".
                        - Take a photo of the barcode or type in the entire number shown on the barcode, including the numbers on the side.
                        - If the barcode isn't linked with a food...
                            - You can add that food by going to the "Add Food from Barcode" tab and select the category or type in a new one.
                            - You can link it to a food by going to the "Assign Barcode to Food" and selecting the food.
                                - This makes it so that when you use the barcode, it will show up as the food you linked to it.
                        - If the barcode is linked with a food...
                            - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
                            - Click "Unlink with Food" to remove the barcode from the food.""")
            with st.expander("**Share Freezer**", type="compact"):
                st.markdown("""
                    - Download your QR code, print it out, and attach it to your freezer!
                        - Whenever you do anything to your Freezer, you can scan it to add or use your food.
                    - Also, you can copy the Creator or Guest links and share them.""")
            with st.expander("**Edit Freezer Information**", type="compact"):
                st.markdown("""
                    - *This page is not to be confused with "Edit Inventory".*
                    - Here you can rename your Freezer and categories.""")
            with st.expander("**Download Recover Files**", type="compact"):
                st.markdown("""
                    - Here you can download JSON recover files for the Guest and Creator Pages.
                    - To use the file, go to "Open Freezer Menu" in the Home Page and upload your file.
                    - You will automatically be redirected to the corresponding page.""")
            # st.markdown("""
            # *This page is where you go when you scan the QR code*
            #
            # **Add Food**
            # - Select the category or type in a new one.
            # - Select a food or type in a new food.
            # - Type in the quantity of food you're adding.
            # - If you're adding a new food, type in the unit of measurement you will be using.
            # - Click "Add Food!" to add the food.
            #
            # **Use Food**
            # - Select the category of the food you're using.
            # - Select the food.
            # - Type in the quantity of food you're adding.
            # - Click "Use Food!" to use the food.
            #
            # **Edit Inventory**
            # - Look at what food you have.
            # - Edit anything about the food, including the unit of measurement, the name, and the amount.
            #     - You can also delete foods entirely by selecting the row on the left-hand side and pressing the trash can icon.
            # - If you're looking to add or use food that you already entered in FreezerOne and you forgot what section it's in...
            #     - Find it on the Edit Inventory page.
            #     - Click the three dots.
            #     - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
            #
            # **Scan Barcode**
            # - If your food has a barcode on it...
            #     - Select one of the tabs.
            #         - There are two camera tabs because some devices don't work on both tabs.
            #         - If one of them doesn't work, try the other tab. If neither of them work, go to "Manual Entry".
            #     - Take a photo of the barcode or type in the entire number shown on the barcode, including the numbers on the side.
            #     - If the barcode isn't linked with a food...
            #         - You can add that food by going to the "Add Food from Barcode" tab and select the category or type in a new one.
            #         - You can link it to a food by going to the "Assign Barcode to Food" and selecting the food.
            #             - This makes it so that when you use the barcode, it will show up as the food you linked to it.
            #     - If the barcode is linked with a food...
            #         - Click "View on Add Page" or "View on Use Page" depending on what you want to do.
            #         - Click "Unlink with Food" to remove the barcode from the food.
            #
            # **Share Freezer**
            # - Download your QR code, print it out, and attach it to your freezer!
            #     - Whenever you do anything to your Freezer, you can scan it to add or use your food.
            # - Also, you can copy the Creator or Guest links and share them.
            #
            # **Edit Freezer Information**
            # - *This page is not to be confused with "Edit Inventory".*
            # - Here you can rename your Freezer and categories.
            #
            # **Download Recover Files**
            # - Here you can download JSON recover files for the Guest and Creator Pages.
            # - To use the file, go to "Open Freezer Menu" in the Home Page and upload your file.
            # - You will automatically be redirected to the corresponding page.
            # """)
else:
    if "totoast" in st.session_state:
        st.toast(st.session_state.totoast, icon=st.session_state.totoastemoji)
        del st.session_state.totoast, st.session_state.totoastemoji
    fid = st.query_params["fid"]
    cid = st.query_params.get("cid")
    fmeta = json.loads(s3.get_object(Bucket=BUCKET,
                                     Key=r2_key(fid))["Body"].read())
    categories = fmeta["items"]
    fname = fmeta["name"]
    if cid == fmeta["cid"]:
        st.header(f"This is the {fname} Creator Page.")
    setup_session_state("tab_state", "Add Food")
    setup_session_state("tab_navigation", None)
    setup_session_state("creatortabkey", None)
    if st.session_state.get("tab_navigation"):
        # st.write("Tab Navigation:", st.session_state.tab_navigation)
        del st.session_state.tab_state
        st.session_state.tab_state = st.session_state.pop("tab_navigation")
    else:
        st.session_state.tab_state = None
    temptabstate = (st.session_state.get(st.session_state.creatortabkey) if st.session_state.get(
        "creatortabkey") else None) if not st.session_state.get("tab_state") else st.session_state.tab_state
    # st.write(st.session_state.get("tab_state"))
    # st.write(st.session_state.get("creatortabkey"))
    if st.session_state.get("tab_state"):
        st.session_state.creatortabkey = uuid.uuid4().hex
    creatortabs = st.tabs(
        ["Add Food", "Use Food", "Edit Inventory", "Scan Barcode", "Share Freezer", "Edit Freezer Information",
         "Download Recover Files"] if cid == fmeta["cid"] else ["Add Food", "Use Food", "View Inventory",
                                                                "Scan Barcode"], key=st.session_state.creatortabkey,
        default=temptabstate)
    # st.write("Tab State:", st.session_state.tab_state)
    # st.write("Tab Navigation:", st.session_state.tab_navigation)
    with creatortabs[0]:
        category = st.selectbox("What category does the food fall in?", [*categories], accept_new_options=True,
                                index=[*categories].index(
                                    st.session_state.get("page_category")) if st.session_state.get(
                                    "page_category") else 0)
        if not category:
            category = ""
        else:
            category = better_title(category)
        # st.write([*categories[category.title()]].index(st.session_state.get("page_food")) if (st.session_state.get("page_category") and category == st.session_state.get("page_category")) else 0)
        foodname = st.selectbox("What is the food called?",
                                [*categories[category]] if category in [*categories] else [],
                                accept_new_options=True, index=(
                [*categories[category]].index(st.session_state.get("page_food")) if (st.session_state.get(
                    "page_category") and category == st.session_state.get("page_category")) else 0))
        foodname = better_title(foodname)
        with st.container(horizontal=True, vertical_alignment="bottom"):
            foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150)
            if category not in [*categories] or foodname not in (
                    [*categories[category]] if category in [*categories] else []):
                foodunit = st.text_input(
                    "What is the unit of measurement you will use? Separate the plural with a /",
                    placeholder="eg. pound/pounds").lower()
            else:
                foodunit = categories[category][foodname][1]
                st.write(foodunit.split("/")[0] if foodamount == 1 else foodunit.split("/")[1])
        if st.button("Add Food!", type="primary"):
            if foodname and foodunit:
                if "/" in foodunit:
                    if not category in categories:
                        categories[category] = {}
                    if foodname not in categories[category]:
                        categories[category][foodname] = [foodamount, foodunit.lower()]
                    else:
                        categories[category][foodname][0] += foodamount
                    fmeta["items"] = categories
                    s3.put_object(Bucket=BUCKET,
                                  Key=r2_key(fid),
                                  Body=json.dumps(fmeta), )
                    st.session_state.totoast = "Added!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()
                else:
                    st.toast("Please type in a valid food unit, like bunch/bunches", icon=":material/error:")
    with creatortabs[1]:
        if len(categories.keys()) < 1:
            st.error("Create categories to access this page.")
        else:
            foods = st.tabs([*categories], default=st.session_state.get("page_category") if st.session_state.get(
                "page_category") else None, on_change="rerun")
            for i in range(len([*categories])):
                with foods[i]:
                    foodtouse = st.selectbox("What is the food?", [*categories[list(categories.keys())[i]]], index=(
                        [*categories[st.session_state.get("page_category")]].index(
                            st.session_state.get("page_food")) if (
                                st.session_state.get("page_food") and [*categories][i] == st.session_state.get(
                            "page_category")) else 0))
                    if foodtouse is not None:
                        famt = categories[list(categories.keys())[i]][foodtouse][0]
                        if int(famt) == famt:
                            famt = int(famt)
                        f"You have {famt} {categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if categories[list(categories.keys())[i]][foodtouse][0] == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1]} of {foodtouse.lower()}"
                        with st.container(horizontal=True, vertical_alignment="bottom"):
                            amttouse = st.number_input("Amount to use:", 0.0, float(famt), step=1.0, width=150,
                                                       key=f"amttouse{i}")
                            st.write(categories[list(categories.keys())[i]][foodtouse][1].split('/')[
                                         0] if amttouse == 1 else
                                     categories[list(categories.keys())[i]][foodtouse][1].split('/')[1])
                        if amttouse != 0:
                            if st.button("Use Food!", type="primary", key=f"use{i}"):
                                categories[list(categories.keys())[i]][foodtouse][0] -= amttouse
                                fmeta["items"] = categories
                                s3.put_object(Bucket=BUCKET,
                                              Key=r2_key(fid),
                                              Body=json.dumps(fmeta), )
                                st.session_state.totoast = "Used!"
                                st.session_state.totoastemoji = ":material/check:"
                                st.rerun()
    if cid == fmeta["cid"]:
        with creatortabs[2]:
            # if len(categories.keys()) < 1:
            #     st.error("Create categories to access this page.")
            # else:
            #     st.session_state.df = pd.DataFrame(
            #         [[category, key, value[0], ["View on Add Page", "View on Use Page"]]
            #          for category in categories
            #          for key, value in categories[category.title()].items()
            #          ],
            #         columns=["Categories", "Food", "Amount", "bttns"],
            #     )
            #     st.dataframe(st.session_state.df, width="stretch", hide_index=True, height="content", column_config={
            #         "bttns": st.column_config.ButtonColumn("View on Add/Use Page", on_click=handle_action,
            #                                                key="action_click")})
            if len(categories.keys()) < 1:
                st.error("Create categories to access this page.")
            else:
                foodtabs = st.tabs(list(categories.keys()))
                for i in range(len(list(categories.keys()))):
                    with foodtabs[i]:
                        edit_category = list(categories.keys())[i]
                        st.session_state[f"df{i}"] = pd.DataFrame(
                            [
                                {
                                    "Food": item,
                                    "Amount": values[0],
                                    "Unit": values[1],
                                    "bttns": ["View on Add Page", "View on Use Page"]
                                }
                                for item, values in categories[edit_category].items()
                            ]
                        )

                        # Make sure an empty category still has the right columns
                        if st.session_state[f"df{i}"].empty:
                            st.session_state[f"df{i}"] = pd.DataFrame(columns=["Food", "Amount", "Unit", "bttns"])

                        # Edit it
                        edited_df = st.data_editor(
                            st.session_state[f"df{i}"],
                            num_rows="dynamic",
                            hide_index=True,
                            key=f"foodtabs_{i}",
                            column_config={
                                "Food": st.column_config.TextColumn("Food"),
                                "Amount": st.column_config.NumberColumn("Amount", min_value=0.0),
                                "Unit": st.column_config.TextColumn("Unit"),
                                "bttns": st.column_config.ButtonColumn("View on Add/Use Page",
                                                                       on_click=handle_action_for_creator,
                                                                       key=f"action_click{i}", args=[i])
                            },
                        )

                        # Convert it back to your original structure
                        categories[edit_category] = {
                            row["Food"]: [row["Amount"], row["Unit"]]
                            for _, row in edited_df.iterrows()
                            if row["Food"]
                        }
                        update_s3(categories)
        with creatortabs[3]:
            cameratab1, cameratab2, cameratab3 = st.tabs(["Camera", "Alternative Camera", "Manual Entry"],
                                                         on_change="rerun")
            fail = False
            with cameratab1:
                enable = st.checkbox("Enable camera")
                picture1 = st.camera_input("Take a picture", disabled=not enable)
            with cameratab2:
                picture2 = st.file_uploader("Upload a Picture", type="image")
            with cameratab3:
                st.write("Write a UPC to detect manually.")
                with st.popover("Example"):
                    st.image("barcode.png", width="stretch")
                upc_input = st.text_input("Enter UPC (12 digits)", max_chars=12)
                if upc_input:
                    if not upc_input.isdigit():
                        st.error("UPC must contain numbers only.")
                        # st.stop()
                    elif len(upc_input) < 12:
                        st.error(f"UPC is too short. Entered {len(upc_input)}/12 digits. Please keep typing...")
                        fail = True
                        # st.stop()
            if cameratab1.open:
                if picture1:
                    file_bytes = np.asarray(bytearray(picture1.read()), dtype=np.uint8)
                    open_cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    barcode = zx.read_barcode(open_cv_img)
                    try:
                        raw_text = barcode.text
                    except:
                        st.error("No barcode in picture. Please try again.")
                        fail = True
                        # st.stop()
                    if not fail:
                        if len(raw_text) == 13 and raw_text.startswith("0"):
                            upc_input = raw_text[1:]
                        else:
                            upc_input = raw_text
                else:
                    st.error("No picture.")
                    fail = True
                    # st.stop()
            elif cameratab2.open:
                if picture2:
                    file_bytes = np.asarray(bytearray(picture2.read()), dtype=np.uint8)
                    open_cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    barcode = zx.read_barcode(open_cv_img)
                    try:
                        raw_text = barcode.text
                    except:
                        st.error("No barcode in picture. Please try again.")
                        fail = True
                        # st.stop()
                    if not fail:
                        if len(raw_text) == 13 and raw_text.startswith("0"):
                            upc_input = raw_text[1:]
                        else:
                            upc_input = raw_text
                else:
                    st.error("No picture.")
                    fail = True
                    # st.stop()
            known_upcs = get_upcs(categories)
            if upc_input and not fail:
                st.divider()
                if not upc_input in [*known_upcs]:
                    barcodetabs = st.tabs(["Find Food From Barcode", "Assign Barcode to Food"],
                                          default="Find Food From Barcode")
                    with barcodetabs[0]:
                        jsondata = requests.get(f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc_input}")
                        data = json.loads(jsondata.text)
                        if not data.get("items"):
                            st.error(
                                "No food found. This could be because...\n- Our database is ratelimiting you\n- Our database does not contain the food you scanned.")
                        if data.get("items"):
                            with st.popover("Check with Image"):
                                img_url = data["items"][0]["images"][0]
                                st.image(img_url)
                            category = st.selectbox("Choose Category",
                                                    [*categories, *data["items"][0]["category"].split(" > ")],
                                                    index=len(
                                                        [*categories, *data["items"][0]["category"].split(" > ")]) - 1,
                                                    accept_new_options=True)
                            category = better_title(category)
                            foodname = st.text_input("What is the food called?",
                                                     value=better_title(data["items"][0]["title"]))
                            foodname = better_title(foodname)
                            with st.container(horizontal=True):
                                foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150,
                                                             key="barcode_foodamount", value=1.0)
                                foodunit = st.text_input(
                                    "What is the unit of measurement you will use? Separate the plural with a /",
                                    placeholder="eg. pound/pounds", value="package/packages",
                                    key="barcode_foodunit").lower()
                            if st.button("Add Food", type="primary", key="barcode_add_food"):
                                if foodamount > 0 and foodunit:
                                    if category not in [*categories]:
                                        categories[category] = {}
                                    categories[category][foodname] = [
                                        (categories[category][foodname][0] + foodamount) if foodname in [
                                            *categories[category]] else foodamount, foodunit, upc_input]
                                    fmeta["items"] = categories
                                    s3.put_object(Bucket=BUCKET,
                                                  Key=r2_key(fid),
                                                  Body=json.dumps(fmeta), )
                    with barcodetabs[1]:
                        foods = target_categories = {target: category for category, targets in categories.items() for
                                                     target in targets}
                        foodtoaddbarcodeto = st.selectbox("Choose what food to link to this barcode.", [*foods])
                        if st.button("Link!", type="primary", key="barcode_link"):
                            categories[foods[foodtoaddbarcodeto]][foodtoaddbarcodeto][2] = upc_input
                            update_s3(categories)
                            st.session_state.totoast = "Linked successfully!"
                            st.session_state.totoastemoji = ":material/check:"
                            st.rerun()
                else:
                    food = known_upcs[upc_input]
                    foods = {food: category for category in categories.values() for food in category}
                    with st.container(horizontal=True):
                        if st.button("View on Add Page", width="stretch"):
                            st.session_state.tab_navigation = "Add Food"
                            st.session_state.page_category = food[0]
                            st.session_state.page_food = food[1]
                            st.rerun()
                        if st.button("View on Use Page", width="stretch"):
                            st.session_state.tab_navigation = "Use Food"
                            st.session_state.page_category = food[0]
                            st.session_state.page_food = food[1]
                            st.rerun()
                    if st.button("Unlink with food", type="primary", key="barcode_unlink", width="stretch"):
                        categories[food[0]][food[1]][2] = None
                        update_s3(categories)
                        st.session_state.totoast = "Unlinked successfully!"
                        st.session_state.totoastemoji = ":material/check:"
                        st.rerun()
        with creatortabs[4]:
            guest_url = BASE_URL + f"/?fid={fid}"
            creator_url = BASE_URL + f"/?fid={fid}&cid={cid}"
            qr = qrcode.make(guest_url)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)

            # Display QR and links
            with st.container(horizontal_alignment="center"):
                with st.container(border=True, width="content", horizontal_alignment="center"):
                    st.header("Guest QR Code Generator", text_alignment="center")
                    st.image(buf, width=200)
                    st.download_button(
                        label="Download QR code",
                        data=buf.getvalue(),
                        file_name="qr.png",
                        mime="image/png",
                        type="primary"
                    )
                    "Print this out and put it on your freezer so you can scan it and access your data in a snap!"
            with st.container(border=True):
                st.write("Guest URL:")
                st.code(guest_url, language=None)
            with st.container(border=True):
                st.write("Creator URL:")
                st.code(creator_url, language=None)
        with creatortabs[5]:
            with st.container(horizontal=True, vertical_alignment="bottom"):
                newname = st.text_input("What is the new name for your Freezer?")
                if st.button("Rename Freezer!", type="primary"):
                    if newname:
                        fmeta["name"] = newname
                        s3.put_object(Bucket=BUCKET,
                                      Key=r2_key(fid),
                                      Body=json.dumps(fmeta))
                        st.session_state.totoast = "Freezer renamed!"
                        st.session_state.totoastemoji = ":material/check:"
                        st.rerun()
            with st.container(horizontal=True, vertical_alignment="bottom"):
                "Replace"
                old = st.selectbox("", list(categories.keys()))
                "with"
                new = st.text_input("")
                new = better_title(new)
                if st.button("Replace", type="primary", width="stretch") and new:
                    fmeta["items"][new] = fmeta["items"][old]
                    del fmeta["items"][old]
                    s3.put_object(Bucket=BUCKET,
                                  Key=r2_key(fid),
                                  Body=json.dumps(fmeta))
                    st.session_state.totoast = "Category renamed!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()
        with creatortabs[6]:
            st.write("Download these files and share them to share your freezer or recover it if you close the tab!")
            guestdata = json.dumps({"access": "guest", "fid": fid})
            creatordata = json.dumps({"access": "creator", "fid": fid, "cid": cid})
            with st.container(horizontal=True):
                st.download_button("Guest file", guestdata, file_name=f"{fmeta['name']} Guest Recover File",
                                   width="stretch", mime="application/json", type="primary")
                st.download_button("Creator file", creatordata, file_name=f"{fmeta['name']} Creator Recover File",
                                   width="stretch", mime="application/json", type="primary")
    #     else:
    #         st.error(f"Incorrect Freezer Creator ID!")
    # else:
    #     if "totoast" in st.session_state:
    #         st.toast(st.session_state.totoast, icon=st.session_state.totoastemoji)
    #         del st.session_state.totoast, st.session_state.totoastemoji
    #     fid = st.query_params["fid"]
    #     fmeta = json.loads(s3.get_object(Bucket=BUCKET,
    #                                      Key=r2_key(fid),
    #                                      )["Body"].read())
    #     categories = fmeta["items"]
    #     fname = fmeta["name"]
    #     if st.session_state.get("tab_navigation"):
    #         del st.session_state.tab_state
    #         st.session_state.tab_state = st.session_state.pop("tab_navigation")
    #     guesttabs = st.tabs(["Add Food", "Use Food", "View Inventory", "Scan Barcode"], key="tab_state", default=st.session_state.tab_state, on_change="rerun")
    #     with guesttabs[0]:
    #         category = st.selectbox("What category does the food fall in?", [*categories], accept_new_options=True, index=[*categories].index(st.session_state.get("page_category")) if st.session_state.get("page_category") else 0)
    #         if not category:
    #             category = ""
    #         foodname = st.selectbox("What is the food called?", [*categories[category.title()]] if category.title() in [*categories] else [], accept_new_options=True, index=([*categories[category.title()]].index(st.session_state.get("page_food")) if st.session_state.get("page_category") and category == st.session_state.get("page_category") else 0))
    #         with st.container(horizontal=True):
    #             foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150)
    #             if category.title() not in [*categories] or foodname not in ([*categories[category.title()]] if category.title() in [*categories] else []):
    #                 foodunit = st.text_input("What is the unit of measurement you will use? Separate the plural with a /",
    #                                                placeholder="eg. pound/pounds").lower()
    #             else:
    #                 foodunit = categories[category.title()][foodname.title()][1]
    #                 st.write(foodunit.split("/")[0] if foodamount == 1 else foodunit.split("/")[1])
    #         if st.button("Add Food!"):
    #             if foodname and foodunit:
    #                 if "/" in foodunit:
    #                     if not category.title() in categories:
    #                         categories[category.title()] = {}
    #                     if foodname not in categories[category.title()]:
    #                         categories[category.title()][foodname.title()] = [foodamount, foodunit.lower()]
    #                     else:
    #                         categories[category.title()][foodname.title()][0] += foodamount
    #                     fmeta["items"] = categories
    #                     s3.put_object(Bucket=BUCKET,
    #                                   Key=r2_key(fid),
    #                                   Body=json.dumps(fmeta),)
    #                     st.session_state.totoast = "Added!"
    #                     st.session_state.totoastemoji = ":material/check:"
    #                     st.rerun()
    #                 else:
    #                     st.toast("Please type in a valid food unit, like bunch/bunches", icon=":material/error:")
    #     with guesttabs[1]:
    #         if len(categories.keys()) < 1:
    #             st.error("Create categories to access this page.")
    #         else:
    #             foods = st.tabs([*categories], default=st.session_state.get("page_category") if st.session_state.get("page_category") else None, on_change="rerun")
    #             for i in range(len([*categories])):
    #                 with foods[i]:
    #                     foodtouse = st.selectbox("What is the food?",[*categories[list(categories.keys())[i]]], index=([*categories[st.session_state.get("page_category")]].index(st.session_state.get("page_food")) if (st.session_state.get("page_food") and [*categories][i] == st.session_state.get("page_category")) else 0))
    #                     if foodtouse is not None:
    #                         famt = categories[list(categories.keys())[i]][foodtouse][0]
    #                         if int(famt) == famt:
    #                             famt = int(famt)
    #                         f"You have {famt} {categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if categories[list(categories.keys())[i]][foodtouse][0] == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1]} of {foodtouse.lower()}"
    #                         with st.container(horizontal=True, vertical_alignment="bottom"):
    #                             amttouse = st.number_input("Amount to use:", 0.0, float(famt), step=1.0, width=150, key=f"amttouse{i}")
    #                             st.write(categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if amttouse == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1])
    #                         if amttouse != 0:
    #                             if st.button("Use!", type="primary", key=f"use{i}"):
    #                                 categories[list(categories.keys())[i]][foodtouse][0] -= amttouse
    #                                 fmeta["items"] = categories
    #                                 s3.put_object(Bucket=BUCKET,
    #                                               Key=r2_key(fid),
    #                                               Body=json.dumps(fmeta),)
    #                                 st.session_state.totoast = "Used!"
    #                                 st.session_state.totoastemoji = ":material/check:"
    #                                 st.rerun()
    else:
        with creatortabs[2]:
            if len(categories.keys()) < 1:
                st.error("Create categories to access this page.")
            else:
                st.session_state.df = pd.DataFrame(
                    [[category, key, value[0], ["View on Add Page", "View on Use Page"]]
                     for category in categories
                     for key, value in categories[category].items()
                     ],
                    columns=["Categories", "Food", "Amount", "bttns"],
                )
                st.dataframe(st.session_state.df, width="stretch", hide_index=True, height="content", column_config={
                    "bttns": st.column_config.ButtonColumn("View on Add/Use Page", on_click=handle_action,
                                                           key="action_click")})
        with creatortabs[3]:
            cameratab1, cameratab2, cameratab3 = st.tabs(["Camera", "Alternative Camera", "Manual Entry"],
                                                         on_change="rerun")
            with cameratab1:
                enable = st.checkbox("Enable camera")
                picture1 = st.camera_input("Take a picture", disabled=not enable)
            with cameratab2:
                picture2 = st.file_uploader("Upload a Picture", type="image")
            with cameratab3:
                st.write("Write a UPC to detect manually.")
                with st.popover("Example"):
                    st.image("barcode.png", width="stretch")
                upc_input = st.text_input("Enter UPC (12 digits)", max_chars=12)
                if upc_input:
                    if not upc_input.isdigit():
                        st.error("UPC must contain numbers only.")
                        # st.stop()
                    elif len(upc_input) < 12:
                        st.error(f"UPC is too short. Entered {len(upc_input)}/12 digits. Please keep typing...")
                        # st.stop()
            if cameratab1.open:
                if picture1:
                    file_bytes = np.asarray(bytearray(picture1.read()), dtype=np.uint8)
                    open_cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    barcode = zx.read_barcode(open_cv_img)
                    fail = False
                    try:
                        raw_text = barcode.text
                    except:
                        st.error("No barcode in picture.")
                        fail = True
                        # st.stop()
                    if len(raw_text) == 13 and raw_text.startswith("0"):
                        upc_input = raw_text[1:]
                    else:
                        upc_input = raw_text
                else:
                    st.error("No picture.")
                    fail = True
                    # st.stop()
            elif cameratab2.open:
                if picture2:
                    file_bytes = np.asarray(bytearray(picture2.read()), dtype=np.uint8)
                    open_cv_img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    barcode = zx.read_barcode(open_cv_img)
                    fail = False
                    try:
                        raw_text = barcode.text
                    except:
                        st.error("No barcode in picture.")
                        fail = True
                        # st.stop()
                    if len(raw_text) == 13 and raw_text.startswith("0"):
                        upc_input = raw_text[1:]
                    else:
                        upc_input = raw_text
                else:
                    st.error("No picture.")
                    fail = True
                    # st.stop()
            known_upcs = get_upcs(categories)
            if upc_input:
                st.divider()
                if not upc_input in [*known_upcs]:
                    barcodetabs = st.tabs(["Find Food From Barcode", "Assign Barcode to Food"],
                                          default="Find Food From Barcode")
                    with barcodetabs[0]:
                        jsondata = requests.get(f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc_input}")
                        data = json.loads(jsondata.text)
                        if not data.get("items"):
                            st.write(data)
                        if data.get("items"):
                            with st.popover("Check with Image"):
                                img_url = data["items"][0]["images"][0]
                                st.image(img_url)
                            category = st.selectbox("Choose Category",
                                                    [*categories, *data["items"][0]["category"].split(" > ")],
                                                    index=len(
                                                        [*categories, *data["items"][0]["category"].split(" > ")]) - 1,
                                                    accept_new_options=True)
                            foodname = st.text_input("What is the food called?",
                                                     value=better_title(data["items"][0]["title"]))
                            category = better_title(category)
                            foodname = better_title(foodname)
                            with st.container(horizontal=True):
                                foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150,
                                                             key="barcode_foodamount", value=1.0)
                                foodunit = st.text_input(
                                    "What is the unit of measurement you will use? Separate the plural with a /",
                                    placeholder="eg. pound/pounds", value="package/packages",
                                    key="barcode_foodunit").lower()
                            if st.button("Add Food", type="primary", key="barcode_add_food"):
                                if foodamount > 0 and foodunit:
                                    if category not in [*categories]:
                                        categories[category] = {}
                                    categories[category][foodname] = [
                                        (categories[category][foodname][0] + foodamount) if foodname in [
                                            *categories[category]] else foodamount, foodunit, upc_input]
                                    fmeta["items"] = categories
                                    s3.put_object(Bucket=BUCKET,
                                                  Key=r2_key(fid),
                                                  Body=json.dumps(fmeta))
                    with barcodetabs[1]:
                        foods = target_categories = {target: category for category, targets in categories.items() for
                                                     target in targets}
                        foodtoaddbarcodeto = st.selectbox("Choose what food to link to this barcode.", [*foods])
                        if st.button("Link!", type="primary", key="barcode_link"):
                            categories[foods[foodtoaddbarcodeto]][foodtoaddbarcodeto][2] = upc_input
                            update_s3(categories)
                            st.session_state.totoast = "Linked successfully!"
                            st.session_state.totoastemoji = ":material/check:"
                            st.rerun()
                else:
                    food = known_upcs[upc_input]
                    foods = {food: category for category in categories.values() for food in category}
                    with st.container(horizontal=True):
                        if st.button("View on Add Page", width="stretch"):
                            st.session_state.tab_navigation = "Add Food"
                            st.session_state.page_category = food[0]
                            st.session_state.page_food = food[1]
                            st.rerun()
                        if st.button("View on Use Page", width="stretch"):
                            st.session_state.tab_navigation = "Use Food"
                            st.session_state.page_category = food[0]
                            st.session_state.page_food = food[1]
                            st.rerun()
                    if st.button("Unlink with food", type="primary", key="barcode_unlink", width="stretch"):
                        categories[food[0]][food[1]][2] = None
                        update_s3(categories)
                        st.session_state.totoast = "Unlinked successfully!"
                        st.session_state.totoastemoji = ":material/check:"
                        st.rerun()
