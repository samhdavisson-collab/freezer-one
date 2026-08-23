import io
import time

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
                  Body=json.dumps(fmeta),)

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{st.secrets['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=st.secrets["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

BUCKET = st.secrets["R2_BUCKET"]
BASE_URL = "freezerone.streamlit.app" #replace later!!!
# setup_session_state("page", "home")

setup_session_state("guest_tab_state", "Add Food")

def go_to_add():
    st.session_state.go_to_add = True

def go_to_use():
    st.session_state.go_to_use = True

def handle_action():
    click = st.session_state.action_click
    df = st.session_state.df
    if "View on Add Page" in click["label"]:
        # st.session_state.add_clicked_row = click
        # st.session_state.add_page_start = True
        # st.session_state.use_page_start = False
        st.session_state.guest_tab_navigation = "Add Food"
    elif "View on Use Page" in click["label"]:
        # st.session_state.add_page_start = False
        # st.session_state.use_page_start = True
        st.session_state.guest_tab_navigation = "Use Food"
    st.session_state.page_category = df["Categories"][click["row"]]
    st.session_state.page_food = df["Food"][click["row"]]
    temp = st.empty()
    temp.write(st.session_state.get("guest_tab_state"))
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
        if st.button("Create!"):
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
        st.write("Here you can go back to your Freezer Admin or Freezer Guest page.")
        gobackfile = st.file_uploader("Upload your Recover file", type="json")
        if gobackfile:
            file = json.load(gobackfile)
            try:
                if file["access"] == "admin":
                    st.query_params["cid"] = file["cid"]
                st.query_params["fid"] = file["fid"]
                st.rerun()
            except Exception as e:
                st.error("Invalid file uploaded!")
                e
                file
    with hometabs[2]:
        st.write("welcome")
elif "cid" in st.query_params:
    if "totoast" in st.session_state:
        st.toast(st.session_state.totoast, icon=st.session_state.totoastemoji)
        del st.session_state.totoast, st.session_state.totoastemoji
    fid = st.query_params["fid"]
    cid = st.query_params["cid"]
    fmeta = json.loads(s3.get_object(Bucket=BUCKET,
                          Key=r2_key(fid),)["Body"].read())
    categories = fmeta["items"]
    fname = fmeta["name"]
    if cid == fmeta["cid"]:
        st.header(f"This is the {fname} Creator Page.")
        creatortabs = st.tabs(["Add Categories", "Add Food", "Adjust Amounts", "Share Freezer", "Edit Freezer", "Download Recover Files"])
        with creatortabs[0]:
            category = st.text_input(f"What is the category's name?")
            if st.button("Add Category!", width="stretch", type="primary"):
                if category:
                    category = category.title()
                    categories[category.title()] = {}
                    fmeta["items"] = categories
                    s3.put_object(Bucket=BUCKET,
                                  Key=r2_key(fid),
                                  Body=json.dumps(fmeta),
                                  )
                    st.session_state.totoast = "Category added!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()
        with creatortabs[1]:
            if len([*categories]) > 0:
                foodcategory = st.selectbox("What category does the food fall in?", categories).title()
                foodname = st.text_input("What is the food called? Be sure to pluralize it!", placeholder="eg. grapes").title()
                with st.container(horizontal=True):
                    foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150)
                    foodunit = st.text_input("What is the unit of measurement you will use? Separate the plural with a /", placeholder="eg. bunch/bunches").lower()
                if st.button("Add Food!"):
                    if foodname and foodunit:
                        if "/" in foodunit:
                            fmeta["items"][foodcategory][foodname] = [foodamount, foodunit, None]
                            s3.put_object(Bucket=BUCKET,
                                          Key=r2_key(fid),
                                          Body=json.dumps(fmeta),
                                          )
                            st.session_state.totoast = "Food added!"
                            st.session_state.totoastemoji = ":material/check:"
                            st.rerun()
                        else:
                            st.toast("Please type in a valid food unit, like bunch/bunches", icon=":material/error:")
            else:
                st.error("Create categories to access this page.")
        with creatortabs[2]:
            if len(categories.keys()) < 1:
                st.error("Create categories to access this page.")
            else:
                foodtabs = st.tabs(list(categories.keys()))
                for i in range(len(list(categories.keys()))):
                    with foodtabs[i]:
                        edit_category = list(categories.keys())[i]
                        df = pd.DataFrame(
                            [
                                {
                                    "item": item,
                                    "quantity": values[0],
                                    "unit": values[1],
                                }
                                for item, values in categories[edit_category].items()
                            ]
                        )

                        # Make sure an empty category still has the right columns
                        if df.empty:
                            df = pd.DataFrame(columns=["item", "quantity", "unit"])

                        # Edit it
                        edited_df = st.data_editor(
                            df,
                            num_rows="dynamic",
                            hide_index=True,
                            key=f"foodtabs_{i}",
                            column_config={
                                "item": st.column_config.TextColumn("Item"),
                                "quantity": st.column_config.NumberColumn("Quantity", min_value=0.0),
                                "unit": st.column_config.TextColumn("Unit"),
                            },
                        )

                        # Convert it back to your original structure
                        categories[edit_category] = {
                            row["item"]: [row["quantity"], row["unit"]]
                            for _, row in edited_df.iterrows()
                            if row["item"]
                        }
                        update_s3(categories)
        with creatortabs[3]:
            guest_url = BASE_URL + f"/?fid={fid}"
            admin_url = BASE_URL + f"/?fid={fid}&cid={cid}"
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
                st.code(admin_url, language=None)

        #     categorytabs = st.tabs(list(categories.keys()))
        #     edited_categories = {}
        #     for i in range(len(list(categories.keys()))):
        #         edited_categories[i] = pd.DataFrame(categories[list(categories.keys())[i]])
        #         st.data_editor(edited_categories[i], hide_index=True, on_change=update_s3(edited_categories[i].to_json()))
        # categories
        with creatortabs[4]:
            with st.container(horizontal=True, vertical_alignment="bottom"):
                newname = st.text_input("What is the new name for your Freezer?")
                if st.button("Rename Freezer!", type="primary"):
                    if newname:
                        fmeta["name"] = newname
                        s3.put_object(Bucket=BUCKET,
                                      Key=r2_key(fid),
                                      Body=json.dumps(fmeta),)
                        st.session_state.totoast = "Freezer renamed!"
                        st.session_state.totoastemoji = ":material/check:"
                        st.rerun()
            with st.container(horizontal=True, vertical_alignment="bottom"):
                "Replace"
                old = st.selectbox("", list(categories.keys()))
                "with"
                new = st.text_input("")
                if st.button("Replace", type="primary", width="stretch") and new:
                    fmeta["items"][new.title()] = fmeta["items"][old]
                    del fmeta["items"][old]
                    s3.put_object(Bucket=BUCKET,
                                  Key=r2_key(fid),
                                  Body=json.dumps(fmeta),)
                    st.session_state.totoast = "Category renamed!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()
        with creatortabs[5]:
            st.write("Download these files and share them to share your freezer or recover it if you close the tab!")
            guestdata = json.dumps({"access":"guest","fid":fid})
            admindata = json.dumps({"access":"admin","fid":fid,"cid":cid})
            with st.container(horizontal=True):
                st.download_button("Guest file", guestdata, width="stretch", mime="application/json", type="primary")
                st.download_button("Admin file", admindata, width="stretch", mime="application/json", type="primary")
    else:
        st.error(f"Incorrect Freezer Creator ID!")
else:
    if "totoast" in st.session_state:
        st.toast(st.session_state.totoast, icon=st.session_state.totoastemoji)
        del st.session_state.totoast, st.session_state.totoastemoji
    fid = st.query_params["fid"]
    fmeta = json.loads(s3.get_object(Bucket=BUCKET,
                                     Key=r2_key(fid),
                                     )["Body"].read())
    categories = fmeta["items"]
    fname = fmeta["name"]
    # if st.session_state.get("add_page_start"):
    #     # add_clicked_row = st.session_state.add_clicked_row
    #     # add_clicked_row
    #     # "add_clicked_row" in st.session_state
    #     # st.session_state
    #     # row = -1
    #     # categoryidx = 0
    #     # foodidx = 0
    #     # while row < add_clicked_row:
    #     #     row += 1
    #     #     foodidx += 1
    #     #     if foodidx > len(categories[categories.keys()[categoryidx]]):
    #     #         foodidx = -1
    #     #         categoryidx += 1
    #     # addtab = categories.keys()[categoryidx]
    #     # addtabselectbox = categories[categories.keys()[categoryidx]]
    #     # addtab
    #     # addtabselectbox
    #     st.write(st.session_state.get("add_page_start"))
    #     guesttabs = st.tabs(["Add Food", "Use Food", "View Inventory"], default="Add Food")
    # elif st.session_state.get("use_page_start"):
    #     st.write(st.session_state.get("use_page_start"))
    #     guesttabs = st.tabs(["Add Food", "Use Food", "View Inventory"], default="Use Food")
    # else:
    #     guesttabs = st.tabs(["Add Food", "Use Food", "View Inventory"])
    # if "guest_tab_state" not in st.session_state:
    # if st.session_state.get("guest_tab_state"):
    #     del st.session_state.guest_tab_state
    # if st.session_state.get("add_page_start"):
    #     # if st.session_state.get("guest_tab_state") != "Add Food": st.toast("Add Page", icon=":material/tab_move:")
    #     st.session_state["guest_tab_state"] = "Add Food"
    # elif st.session_state.get("use_page_start"):
    #     # if st.session_state.get("guest_tab_state") != "Use Food": st.toast("Use Page", icon=":material/tab_move:")
    #     st.session_state["guest_tab_state"] = "Use Food"
    # else:
    #     st.session_state["guest_tab_state"] = "Add Food"
    #     # st.toast("No Page")
    # "___BEFORE___"
    # "navigation:"
    # st.write(st.session_state.get("guest_tab_navigation"))
    # "guest_tab_state: "
    # st.session_state.guest_tab_state
    if st.session_state.get("guest_tab_navigation"):
        # st.success(f"Guest tab navigation enabled {time.time()}")
        del st.session_state.guest_tab_state
        st.session_state.guest_tab_state = st.session_state.pop("guest_tab_navigation")
    # "___AFTER___"
    # "navigation:"
    # st.write(st.session_state.get("guest_tab_navigation"))
    # "guest_tab_state: "
    # st.session_state.guest_tab_state

    # 2. Render ONE stable tab widget with a key
    guesttabs = st.tabs(["Add Food", "Use Food", "View Inventory", "Scan Barcode"], key="guest_tab_state", default=st.session_state.guest_tab_state, on_change="rerun")
    # guesttabs = st.segmented_control("Food", ["Add Food", "Use Food", "View Inventory"], key="guest_tab_state", label_visibility="collapsed")
    with guesttabs[0]:
        # category = st.selectbox("What category does the food fall in?", [*categories, "New" if "New" not in categories else "Use New"], index=[*categories].index(st.session_state.get("add_page_category")))
        # if category == ("New" if "New" not in categories else "Use New"):
        #     cattouse = st.text_input("What is the new category called?", placeholder="eg. meat").title()
        # else:
        #     cattouse = category
        # foodname = st.selectbox("What is the food called?", [*categories[cattouse], "New" if "New" not in categories[cattouse] else "Use New"] if cattouse in categories else ["New"], index=[*categories[cattouse]].index(st.session_state.get("add_page_food")))
        # if foodname == ("New" if "New" not in (categories[cattouse] if cattouse in categories else []) else "Use New"):
        #     foodtouse = st.text_input("What is the new food called? Be sure to pluralize it!", placeholder="eg. beef")
        # else:
        #     foodtouse = foodname
        # with st.container(horizontal=True):
        #     foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150)
        #     if foodname == ("New" if "New" not in (categories[cattouse] if cattouse in categories else []) else "Use New"):
        #         foodunit = st.text_input("What is the unit of measurement you will use? Separate the plural with a /",
        #                              placeholder="eg. pound/pounds")
        #     else:
        #         foodunit = categories[cattouse][foodtouse.title()][1]
        # if st.button("Add Food!"):
        #     if foodname and foodunit:
        #         if not cattouse in categories:
        #             categories[cattouse] = {}
        #         if foodtouse.title() not in categories[cattouse]:
        #             categories[cattouse][foodtouse.title()] = [foodamount, foodunit.lower()]
        #         fmeta["items"] = categories
        #         fmeta["items"][cattouse][foodtouse.title()] = [(categories[cattouse][foodtouse.title()][0] if foodname != ("New" if "New" not in (categories[cattouse] if cattouse in categories else []) else "Use New") else 0) +foodamount, foodunit.lower()]
        #         categories = fmeta["items"]
        #         s3.put_object(Bucket=BUCKET,
        #                       Key=r2_key(fid),
        #                       Body=json.dumps(fmeta),
        #                       )
        #         st.session_state.totoast = "Added!"
        #         st.session_state.totoastemoji = "✅"
        #         st.rerun()
        category = st.selectbox("What category does the food fall in?", [*categories], accept_new_options=True, index=[*categories].index(st.session_state.get("page_category")) if st.session_state.get("page_category") else 0)
        if not category:
            category = ""
        foodname = st.selectbox("What is the food called?", [*categories[category.title()]] if category.title() in [*categories] else [], accept_new_options=True, index=([*categories[category.title()]].index(st.session_state.get("page_food")) if st.session_state.get("page_category") and category == st.session_state.get("page_category") else 0))
        with st.container(horizontal=True):
            foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150)
            if category.title() not in [*categories] or foodname not in ([*categories[category.title()]] if category.title() in [*categories] else []):
                foodunit = st.text_input("What is the unit of measurement you will use? Separate the plural with a /",
                                               placeholder="eg. pound/pounds").lower()
            else:
                foodunit = categories[category.title()][foodname.title()][1]
        if st.button("Add Food!"):
            if foodname and foodunit:
                if "/" in foodunit:
                    if not category.title() in categories:
                        categories[category.title()] = {}
                    if foodname not in categories[category.title()]:
                        categories[category.title()][foodname.title()] = [foodamount, foodunit.lower()]
                    else:
                        categories[category.title()][foodname.title()][0] += foodamount
                    fmeta["items"] = categories
                    s3.put_object(Bucket=BUCKET,
                                  Key=r2_key(fid),
                                  Body=json.dumps(fmeta),)
                    st.session_state.totoast = "Added!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()
                else:
                    st.toast("Please type in a valid food unit, like bunch/bunches", icon=":material/error:")
    with guesttabs[1]:
        if len(categories.keys()) < 1:
            st.error("Create categories to access this page.")
        else:
            foods = st.tabs([*categories], default=st.session_state.get("page_category") if st.session_state.get("page_category") else None, on_change="rerun")
            for i in range(len([*categories])):
                with foods[i]:
                    foodtouse = st.selectbox("What is the food?",[*categories[list(categories.keys())[i]]], index=([*categories[st.session_state.get("page_category")]].index(st.session_state.get("page_food")) if (st.session_state.get("page_food") and [*categories][i] == st.session_state.get("page_category")) else 0))
                    if foodtouse is not None:
                        famt = categories[list(categories.keys())[i]][foodtouse][0]
                        if int(famt) == famt:
                            famt = int(famt)
                        f"You have {famt} {categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if categories[list(categories.keys())[i]][foodtouse][0] == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1]} of {foodtouse.lower()}"
                        with st.container(horizontal=True, vertical_alignment="bottom"):
                            amttouse = st.number_input("Amount to use:", 0.0, float(famt), step=1.0, width=150, key=f"amttouse{i}")
                            st.write(categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if amttouse == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1])
                        if amttouse != 0:
                            if st.button("Use!", type="primary", key=f"use{i}"):
                                categories[list(categories.keys())[i]][foodtouse][0] -= amttouse
                                fmeta["items"] = categories
                                s3.put_object(Bucket=BUCKET,
                                              Key=r2_key(fid),
                                              Body=json.dumps(fmeta),)
                                st.session_state.totoast = "Used!"
                                st.session_state.totoastemoji = ":material/check:"
                                st.rerun()
    with guesttabs[2]:
        if len(categories.keys()) < 1:
            st.error("Create categories to access this page.")
        else:
            # foods = st.tabs([*categories])
            # for i in range(len([*categories])):
            #     with foods[i]:
            #         foodtouse = st.selectbox("What food would you like to look up?",[*categories[list(categories.keys())[i]]])
            #         if foodtouse is not None:
            #             famt = categories[list(categories.keys())[i]][foodtouse][0]
            #             if int(famt) == famt:
            #                 famt = int(famt)
            #             if famt > 0:
            #                 st.info(f"You have {famt} {categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if categories[list(categories.keys())[i]][foodtouse][0] == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1]} of {foodtouse.lower()}")
            #             else:
            #                 st.warning(f"You have {famt} {categories[list(categories.keys())[i]][foodtouse][1].split('/')[0] if categories[list(categories.keys())[i]][foodtouse][0] == 1 else categories[list(categories.keys())[i]][foodtouse][1].split('/')[1]} of {foodtouse.lower()}")
            # df = pd.DataFrame((list(categories[list(categories.keys())[i]].keys()) for i in range(5)), ("Category", "Food"))
            # df
            st.session_state.df = pd.DataFrame(
                [[category, key, value[0], ["View on Add Page", "View on Use Page"]]
                 for category in categories
                 for key, value in categories[category.title()].items()
                ],
                columns=["Categories", "Food", "Amount", "bttns"],
            )
            st.dataframe(st.session_state.df, width="stretch", hide_index=True, height="content", column_config={"bttns": st.column_config.ButtonColumn("View on Add/Use Page", on_click=handle_action, key="action_click")})
    with guesttabs[3]:
        # enable = st.checkbox("Enable camera")
        # picture = st.camera_input("Take a picture", disabled=not enable)
        cameratab1, cameratab2, cameratab3 = st.tabs(["Laptop", "Mobile", "Manual"], on_change="rerun")
        with cameratab1:
            enable = st.checkbox("Enable camera")
            picture1 = st.camera_input("Take a picture", disabled=not enable)
        with cameratab2:
            picture2 = st.file_uploader("Upload a Picture", type=["png", "jpg", "jpeg", "heic", "webp"])
        with cameratab3:
            st.write("Write a UPC to detect manually.")
            upc_input = st.text_input("Enter UPC (12 digits)", max_chars=12)

            # Validation logic
            if upc_input:
                # Check 1: Must be exactly digits
                if not upc_input.isdigit():
                    st.error("UPC must contain numbers only.")
                    st.stop()

                # Check 2: Enforce the minimum length of 12
                elif len(upc_input) < 12:
                    st.error(f"UPC is too short. Entered {len(upc_input)}/12 digits. Please keep typing...")
                    st.stop()
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
                    st.stop()
                if len(raw_text) == 13 and raw_text.startswith("0"):
                    upc_input = raw_text[1:]
                else:
                    upc_input = raw_text
            else:
                st.error("No picture.")
                fail = True
                st.stop()
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
                    st.stop()
                if len(raw_text) == 13 and raw_text.startswith("0"):
                    upc_input = raw_text[1:]
                else:
                    upc_input = raw_text
            else:
                st.error("No picture.")
                fail = True
                st.stop()
        known_upcs = get_upcs(categories)
        if upc_input:
            st.divider()
            if not upc_input in [*known_upcs]:
                barcodetabs = st.tabs(["Find Food From Barcode", "Assign Barcode to Food"], default="Find Food From Barcode")
                with barcodetabs[0]:
                    jsondata = requests.get(f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc_input}")
                    data = json.loads(jsondata.text)
                    if not data.get("items"):
                        data
                    if data.get("items"):
                        with st.popover("Check with Image"):
                            img_url = data["items"][0]["images"][0]
                            st.image(img_url)
                        category = st.selectbox("Choose Category", [*categories, *data["items"][0]["category"].split(" > ")], index=len([*categories, *data["items"][0]["category"].split(" > ")])-1, accept_new_options=True)
                        foodname = st.text_input("What is the food called?", value=data["items"][0]["title"].title())
                        with st.container(horizontal=True):
                            foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150, key="barcode_foodamount", value=1.0)
                            foodunit = st.text_input( "What is the unit of measurement you will use? Separate the plural with a /", placeholder="eg. pound/pounds", value="package/packages", key="barcode_foodunit").lower()
                        if st.button("Add Food", type="primary", key="barcode_add_food"):
                            if foodamount > 0 and foodunit:
                                if category.title() not in [*categories]:
                                    categories[category.title()] = {}
                                categories[category.title()][foodname] = [(categories[category.title()][foodname][0] + foodamount) if foodname in [*categories[category.title()]] else foodamount, foodunit, upc_input]
                                fmeta["items"] = categories
                                s3.put_object(Bucket=BUCKET,
                                              Key=r2_key(fid),
                                              Body=json.dumps(fmeta),)
                with barcodetabs[1]:
                    foods = target_categories = {target: category for category, targets in categories.items() for target in targets}
                    foodtoaddbarcodeto = st.selectbox("Choose what food to link to this barcode.", [*foods])
                    if st.button("Link!", type="primary", key="barcode_link"):
                        # st.write(f"Categories: {categories}",
                        #          "================"
                        #          f"Foods: {foods}",
                        #          "================"
                        #          f"Foodtoaddbarcode: {foodtoaddbarcodeto}",)
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
                        st.session_state.guest_tab_navigation="Add Food"
                        st.session_state.page_category = food[0]
                        st.session_state.page_food = food[1]
                        st.rerun()
                    if st.button("View on Use Page", width="stretch"):
                        st.session_state.guest_tab_navigation="Use Food"
                        st.session_state.page_category = food[0]
                        st.session_state.page_food = food[1]
                        st.rerun()
                if st.button("Unlink with food", type="primary", key="barcode_unlink", width="stretch"):
                    categories[food[0]][food[1]][2] = None
                    update_s3(categories)
                    st.session_state.totoast = "Unlinked successfully!"
                    st.session_state.totoastemoji = ":material/check:"
                    st.rerun()




            # st.write(barcode.text)
            # jsondata = requests.get(f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode.text}")
            # data = json.loads(jsondata.text)
            # if data.get("items"):
            #
            #     # st.write(data["items"][0]["title"].title())
            #     # st.write(data["items"][0]["category"].split(" > "))
            #     with st.popover("Check with Image"):
            #         img_url = data["items"][0]["images"][0]
            #         st.image(img_url)
            #     category = st.selectbox("Choose Category", [*categories, *data["items"][0]["category"].split(" > ")], index=len([*categories, *data["items"][0]["category"].split(" > ")])-1, accept_new_options=True)
            #     foodname = st.text_input("What is the food called?", key="barcode_foodname", value=data["items"][0]["title"].title())
            #     if not category in [*categories]:
            #         if category:
            #             category = category.title()
            #         else:
            #             category = ""
            #     with st.container(horizontal=True):
            #         foodamount = st.number_input("Quantity", 0.0, step=1.0, width=150, key="barcode_foodamount", value=1.0)
            #         if category.title() not in [*categories] or foodname not in (
            #         [*categories[category.title()]] if category.title() in [*categories] else []):
            #             foodunit = st.text_input(
            #                 "What is the unit of measurement you will use? Separate the plural with a /",
            #                 placeholder="eg. pound/pounds", value="package/packages", key="barcode_foodunit").lower()
            #         else:
            #             foodunit = categories[category.title()][foodname.title()][1]
            #     if st.button("Add!"):
            #         if foodamount > 0 and foodunit:
            #             if category.title() not in [*categories]:
            #                 categories[category.title()] = {}
            #             categories[category.title()][foodname] = [(categories[category.title()][foodname][0] + foodamount) if foodname in [*categories[category.title()]] else foodamount, foodunit, barcode.text]
            #             fmeta["items"] = categories
            #             s3.put_object(Bucket=BUCKET,
            #                           Key=r2_key(fid),
            #                           Body=json.dumps(fmeta),)
            #
            # else:
            #     st.error("No barcode found!")