# from langchain import hub
# from langchain_core.prompts import SystemMessagePromptTemplate
# from langchain_core.prompts.chat import ChatPromptTemplate
# from langchain_core.prompts.base import BasePromptTemplate
# from langchain_community.callbacks import get_openai_callback

# # # from typing import List

# # # class ChatPromptModifier:
# # #     def __init__(self):
# # #         # Initialize with a base ChatPromptTemplate
# # #         self.prompt: ChatPromptTemplate = hub.pull("hwchase17/structured-chat-agent")

# # #     def add_system_message(self, encouragement, instructions):
# # #         # Create a new System Message Prompt Template
# # #         system_message_content = f"""
# # #             System: {encouragement}

# # #             Here are some important rules for the interaction:
# # #             {instructions}
# # #         """
# # #         new_system_message_prompt = SystemMessagePromptTemplate.from_template(system_message_content)

# # #         # Add the new system message prompt to the existing prompts
# # #         updated_prompts = [new_system_message_prompt] + self.prompt.get_prompts()

# # #         # Re-construct the ChatPromptTemplate with the updated prompts
# # #         self.prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(updated_prompts)


# # #         return self.prompt

# # # # Usage
# # # modifier = ChatPromptModifier()
# # # modifier.add_system_message("Your encouragement message here", "Your instructions here")
# import os
# from langchain.vectorstores.chroma import Chroma
# from langchain_community.embeddings import (
#     BedrockEmbeddings,
#     OpenAIEmbeddings,
#     GooglePalmEmbeddings,
# )
# from config import APP_ROOT
# import chromadb

# # vectordb = Chroma.from_documents(

# #             persist_directory=os.path.join(APP_ROOT, "application", "controllers", "bot", "static", "embeddings"),
# #             collection_name="chatbot_1",
# #         )._collection.get(where={"source":"/home/shadhin/projects/shadhin/genai_flask_app/application/controllers/bot/static/pdfs/sample.pdf"})

# client = chromadb.PersistentClient(
#     path=os.path.join(
#         APP_ROOT, "application", "controllers", "bot", "static", "embeddings"
#     )
# ).get_collection(name="chatbot_5").get()
# print("client", client)

# # for doc in client["documents"]:
# #     # remove the /n from the string
# #     cleaned_doc = doc.replace('\n', ' ')
# #     print("doc:", cleaned_doc)
# #     print("**********************")
# # # Transform the data into a list of dictionaries of ids and documents
# # transformed_data = [{'id': id_val, 'document': doc.replace('\n', ' ')} for id_val, doc in zip(client['ids'], client['documents'])]
# # print("transformed_data", transformed_data)



# #{'ids': ['91d36858-ca15-11ee-9690-07fcf9efb7d7', '91d36859-ca15-11ee-9690-07fcf9efb7d7], 'documents': ['This is a test document', 'This is another test document']}
# # # collection = client.get_collection(
# # #             # name=f"chatbot_{self.chat_bot.id}",
# # #             name="chatbot_1",
# # #         ).get(where={"source":"/home/shadhin/projects/shadhin/genai_flask_app/application/controllers/bot/static/pdfs/sample.pdf"})
# # # print("before",collection)
# # # deleting got ids (from the collection dictionary )  from the entire collection
# # # client.get_collection(
# # #             # name=f"chatbot_{self.chat_bot.id}",
# # #             name="chatbot_1",
# # #         ).delete(where={"source":"/home/shadhin/projects/shadhin/genai_flask_app/application/controllers/bot/static/pdfs/sample.pdf"})
# # # collection = client.get_collection(
# # #             # name=f"chatbot_{self.chat_bot.id}",
# # #             name="chatbot_1",
# # #         ).get(where={"source":"/home/shadhin/projects/shadhin/genai_flask_app/application/controllers/bot/static/pdfs/bdconstituion.pdf"})
# # # print("after",collection)

# # # vectordb = Chroma(
# # #     persist_directory=os.path.join(
# # #         APP_ROOT, "application", "controllers", "bot", "static", "embeddings"
# # #     ),
# # #     collection_name="chatbot_1",
# # # )

# # # print("vectordb", vectordb)
# # # another_vectordb = Chroma(
# # #     persist_directory=os.path.join(
# # #         APP_ROOT, "application", "controllers", "bot", "static", "embeddings"
# # #     ),
# # #     collection_name="kkkj",
# # # )._collection.get(where={"source": "/home/shadhin/projects/shadhin/genai_flask_app/application/controllers/bot/static/pdfs/sample.pdf"})
# # # print("another_vectordb", another_vectordb)

# # prompt = hub.pull("hwchase17/react-chat-json")

# print("prompt", prompt)