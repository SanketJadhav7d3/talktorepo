

import streamlit as st
import requests
from streamlit_agraph import agraph, Node, Edge, Config

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="TalkToRepo", page_icon="⚔️", layout="wide")
st.title("⚔️ TalkToRepo")

# --- Sidebar: Repository Management ---
with st.sidebar:
    st.header("Repository Indexing")
    repo_url = st.text_input("Enter GitHub Repository URL", placeholder="https://github.com/user/repo")

    if st.button("Index Repository", use_container_width=True):
        if repo_url:
            with st.spinner("Indexing repository..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/index_repo",
                        json={"repo_url": repo_url}
                    )
                    if response.status_code == 200:
                        st.success("Repository indexed successfully!")
                    else:
                        st.error("Failed to index repository.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

# --- Project Map Visualization ---
with st.expander("🕸️ Repository Dependency Map", expanded=False):
    if st.button("🗺️ Render Project Map", use_container_width=True):
        with st.spinner("Generating visualization..."):
            try:
                resp = requests.get(f"{BACKEND_URL}/graph")
                if resp.status_code == 200:
                    graph_data = resp.json()
                    if not graph_data["nodes"]:
                        st.info("The repository has no indexed files yet.")
                    else:
                        nodes = [
                            Node(id=n["id"], label=n["label"], color=n["color"], size=20) 
                            for n in graph_data["nodes"]
                        ]
                        edges = [
                            Edge(source=e["source"], target=e["target"]) 
                            for e in graph_data["edges"]
                        ]
                        
                        config = Config(
                            width=1200,
                            height=600,
                            directed=True,
                            physics=True,
                            nodeHighlightBehavior=True,
                            highlightColor="#F7A7A6",
                            collapsible=False,
                        )
                        agraph(nodes=nodes, edges=edges, config=config)
                else:
                    st.error("Failed to fetch graph data from backend.")
            except Exception as e:
                st.error(f"Connection error: {e}")

# --- Chat Interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Re-render thoughts if they exist in history
        if "thoughts" in message and message["thoughts"]:
            with st.expander("🧠 Agent Reasoning", expanded=False):
                for thought in message["thoughts"]:
                    role = thought.get("role")
                    content = thought.get("content")
                    if role == "ai":
                        if "tool_calls" in thought:
                            for call in thought["tool_calls"]:
                                st.status(f"Calling tool: `{call.get('name')}`", state="complete")
                                st.caption(f"Arguments: `{call.get('args')}`")
                        elif content:
                            st.markdown(content)
                    elif role == "tool":
                        with st.container(border=True):
                            st.caption("Tool Output Processed")

        # Re-render file results if they exist in history
        if "results" in message and message["results"]:
            with st.expander("📄 Referenced Code Snippets", expanded=False):
                for result in message["results"]:
                    if isinstance(result, dict):
                        if 'file' in result:
                            st.markdown(f"**File:** `{result['file']}`")
                        st.code(result.get("content", ""), language="python")
        
        st.markdown(message["content"])

# Handle new user input
if query := st.chat_input("Ask a question about the repository..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Call backend for response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(f"{BACKEND_URL}/query", json={"query": query})
            data = response.json()
            
            answer = data.get("answer", "")
            thoughts = data.get("thoughts", [])
            results = data.get("results", [])

            # 1. Display Reasoning
            if thoughts:
                with st.expander("🧠 Agent Reasoning", expanded=False):
                    for thought in thoughts:
                        role = thought.get("role")
                        content = thought.get("content")
                        if role == "ai":
                            if "tool_calls" in thought:
                                for call in thought["tool_calls"]:
                                    st.status(f"Calling tool: `{call.get('name')}`", state="complete")
                                    st.caption(f"Arguments: `{call.get('args')}`")
                            elif content:
                                st.markdown(content)
                        elif role == "tool":
                            st.toast("Tool execution complete", icon="✅")
                            with st.container(border=True):
                                st.caption("Tool Output Processed")

            # 2. Display File Results
            if results:
                with st.expander("📄 Referenced Code Snippets", expanded=False):
                    for result in results:
                        if isinstance(result, dict):
                            if 'file' in result:
                                st.markdown(f"**File:** `{result['file']}`")
                            st.code(result.get("content", ""), language="python")
                        else:
                            st.markdown(f"**Result:** {result}")

            # 3. Display Final Answer
            st.markdown(answer)
            
            # Add assistant response to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": answer, 
                "thoughts": thoughts, 
                "results": results
            })
