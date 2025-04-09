Here’s your README file with improved **text styling**, better formatting using Markdown best practices (headers, code blocks, emojis, emphasis), and clearer section delineation:

---

# 🧠 Notion Calendar & To-Do Agents

This project implements two **AI-powered agents** that interact with Notion to manage your **📅 calendar events** and **✅ to-do list tasks**. Each agent uses the **Notion API** for data operations and the **Gemini API** for natural language understanding and memory.

> Both agents maintain their own **persistent memory**, enabling **context-aware** interactions across sessions.

---

## 🚀 Features

### 📅 Calendar Agent
- 📖 Read existing calendar entries from Notion  
- 🆕 Create new calendar events  
- 🔄 Update existing calendar events  
- 🧠 Retains memory of past interactions for **smarter scheduling**

### ✅ To-Do Agent
- 📋 Read to-do items from Notion  
- ➕ Add new tasks  
- ☑️ Mark tasks as done or update them  
- 🧠 Remembers task context and user instructions for **better task management**

---

## ⚙️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/elhaweet/Notion-ai-agents.git
cd notion-agents
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a `.env` File
Create a `.env` file in the root directory with the following content:

```env
GEMINI_API_KEY=your_google_gemini_api_key
NOTION_API_KEY=your_notion_api_key
NOTION_ENDPOINT=https://api.notion.com/v1
NOTION_CALENDAR_PAGE_ID=your_calendar_page_id
NOTION_TODO_PAGE_ID=your_todo_page_id
```

---

## 🔗 Notion Integration Setup

1. Go to [Notion Integrations](https://www.notion.so/profile/integrations)  
2. Click **"New Integration"**
3. Set it as **Internal**
4. Copy the generated **Notion API key**

For both **Calendar** and **To-Do** pages:
- Create or open a Notion page
- Click the **three-dot menu (⋮)** at the top-right
- Scroll to **Connections → Add the integration**

To get your page IDs:
- Copy them from the Notion page URLs and paste into your `.env` file

---

## 🧪 Usage

Run the main script to start interacting with the agents:

```bash
python main.py
```

Follow the interactive prompts to:
- Choose between the **calendar** or **to-do** agent
- Interact using **natural language**

✅ Each agent **remembers** previous interactions and provides **context-aware** suggestions.

---

## 🗂️ Project Structure

```
main.py               # Entry point for agent selection and execution
calendar_agent.py     # Calendar management logic and memory
todo_agent.py         # To-do list logic and memory
notion_client.py      # Notion API interaction wrapper
gemini_client.py      # Handles Gemini API requests
utils.py              # Utility functions (e.g., date formatting)
```

---

## 📄 License & Author

**Created by:** Amr Elhaweet
📧 **Contact:** [ellhaweet@gmail.com](mailto:ellhaweet@gmail.com)  

© 2025 Amr El-Haweet. All rights reserved.  
This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

Let me know if you want me to:
- Generate a `LICENSE` file (MIT or another type)
- Turn this into a styled GitHub README with badges  
- Add screenshots or example interactions for better clarity

Ready when you are!
