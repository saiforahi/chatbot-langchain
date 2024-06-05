from dotenv import dotenv_values
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import (
    CharacterTextSplitter,
)
import chromadb
import os

from application.schemas.chatbot_schema import ChatbotToolSchema
from services.boto_service.initiator import bedrock_session
from config import APP_ROOT, EMBEDDED_DB_FOLDER
from application.controllers.baseController import BaseController
from application.models.chatbotModel import ChatbotFile, ChatbotTool
from chromadb.utils import embedding_functions
import uuid
from langchain_core.documents import Document
from collections import defaultdict
from database.service import db


class DocumentProcessor(BaseController):
    """
    This class is responsible for embedding the pdf documents and storing them in the chromadb

    Attributes:
        collection_name: name of the collection in the chromadb
        llm_origin: name of the llm from which the embeddings are to be generated

    """

    def __init__(self, collection_name: str, llm_origin: str, meta_data: dict = None):
        if "OPENAI_API_KEY" not in os.environ:
            os.environ["OPENAI_API_KEY"] = dotenv_values(".env").get("OPENAI_API_KEY")
        self.collection_name = collection_name
        self.embedding_function = self.get_embedding_function(llm_origin)
        self.persistent_client = chromadb.PersistentClient(path=EMBEDDED_DB_FOLDER)
        self.meta_data = meta_data

    def get_embedding_function(self, llm_origin: str):
        """
        This function returns the embedding function based on the llm_origin

        Args:
            llm_origin: name of the llm from which the embeddings are to be generated

        Returns:
            embedding_function: embedding function based on the llm_origin

        """
        if llm_origin == "bedrock":
            return embedding_functions.AmazonBedrockEmbeddingFunction(
                session=bedrock_session
            )
        elif llm_origin == "openai":
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY")
            )

        elif llm_origin == "google":
            return embedding_functions.GooglePalmEmbeddingFunction()
        else:
            raise Exception("llm_origin not found")

    def delete_embedded_file_from_chromadb_collection(self, file_path):
        """
        This function deletes the embedded file from the chromadb collection
        by using the file_path to get source and deleting the document from the collection
        by using the where clause.

        Args:
            file_path: path of the file to be deleted

        """
        try:
            try:
                collection = self.persistent_client.get_collection(
                    name=self.collection_name
                )
                print("collection", collection)
            # ValueError: if collection does not exist
            except ValueError:
                print("collection does not exist")
                self.error_response(message="collection does not exist")
            except Exception as e:
                print("error while getting collection", e)
                self.error_response(message="error while getting collection")
            source = file_path
            collection.delete(where={"source": source})
            return self.success_response(
                message=f"file embedded in chromadb deleted successfully"
            )
        except Exception as e:
            print("error while deleting file", e)
            return self.error_response(message="error while deleting embedded file")

    def delete_collection(self):
        """
        This function deletes the collection from the chromadb

        Returns:
            json response
        """
        try:
            self.persistent_client.delete_collection(name=self.collection_name)
            return self.success_response(message="collection deleted successfully")
        except Exception as e:
            print("error while deleting collection", e)
            return self.error_response(message="error while deleting collection")

    def process_pdf_documents(self, file_locations: list[str], new_tool):
        """
        This function processes the pdf documents and stores them in the ChromaDB.

        Args:
            file_locations: file locations of the pdf documents

        Returns:
            Json response
        """
        try:

            documents = self._load_documents(file_locations)
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=10)
            chunked_documents: list[Document] = text_splitter.split_documents(documents)

            collection = self.persistent_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
            )

            sources = {}

            for doc in chunked_documents:
                # Create a new metadata object for each document
                meta_data = self.meta_data.copy()
                meta_data["source"] = doc.metadata["source"]

                # Retrieve metadata for a unique source only once
                if meta_data["source"] not in sources:
                    file = ChatbotFile.query.filter_by(file_location=doc.metadata["source"]).first()
                    if not file:
                        # Handle the case when file is not found
                        meta_data.update(
                            {
                                "file_id": None,
                                "file_location": doc.metadata["source"],
                                "file_name": doc.metadata["source"].split("/")[-1],
                            }
                        )
                    else:
                        sources[meta_data["source"]] = {
                            "file_id": file.id,
                            "file_location": file.file_location,
                            "file_name": file.file_name,
                        }

                meta_data["file_id"] = sources[meta_data["source"]]["file_id"]
                meta_data["file_location"] = sources[meta_data["source"]][
                    "file_location"
                ]
                meta_data["file_name"] = sources[meta_data["source"]]["file_name"]

                collection.add(
                    ids=[str(uuid.uuid1())],
                    metadatas=[meta_data],
                    documents=[doc.page_content],
                )

            return self.success_response(
                message="pdf documents processed successfully",
                data=ChatbotToolSchema(many=False).dump(
                    ChatbotTool.query.get(self.meta_data.get("tool_id"))
                ),
            )
        except Exception as e:
            if new_tool:
                ChatbotTool.query.filter_by(id=self.meta_data.get("tool_id")).delete()

            print("error while processing pdf documents", e)
            return self.error_response(message="error while processing pdf documents")

    def _load_documents(self, file_locations: list[str]):
        """
        This function loads the pdf documents from the pdf folder

        Args:
            file_locations: file locations of the pdf documents

        Returns:
            documents: list of documents
        """
        documents = []
        metadatas = []
        # ids_containing_file_names = []
        for file_location in file_locations:
            loader = PyPDFLoader(file_location)
            loaded_documents = loader.load()
            documents.extend(loaded_documents)

        return documents

    def get_all_files_from_collection_with_metadata(self, chatbot_tools):
        """
        This function gets all the files from the collection with metadata

        Args:
            chatbot_tools: list of chatbot tools

        Returns:
            tools_and_files: list of dictionaries containing tools and files
        """
        try:
            tools_and_files = []

            collection = self.persistent_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
            )

            for chatbot_tool in chatbot_tools:
                # Fetch the data from the collection
                filtered_collection = collection.get(where={"tool_id": chatbot_tool.id})

                # Always include tool information, even if no files are present
                tool_info = {
                    "tool_name": chatbot_tool.name,
                    "tool_id": chatbot_tool.id,
                    "tool_description": chatbot_tool.description,
                    "files": [],
                }

                # Transform the data into a list of dictionaries
                transformed_data = []

                # Create a defaultdict to group documents by unique file information
                grouped_data = defaultdict(
                    lambda: {
                        "file_id": None,
                        "file_location": None,
                        "file_name": None,
                        "source": None,
                        "documents": [],
                    }
                )

                for id_val, doc, metadata in zip(
                        filtered_collection["ids"],
                        filtered_collection["documents"],
                        filtered_collection["metadatas"],
                ):

                    # Split documents by newline characters
                    doc_parts = doc.split("\n")

                    trimmed_parts = [
                        part.strip() for part in doc_parts if part.strip()
                    ]  # Removes empty lines and trims

                    cleaned_doc = ""

                    for i, part in enumerate(trimmed_parts):
                        if (
                                i > 0
                        ):  # If not the first part, decide whether to prepend a space
                            # Check if the last character of the previous part and the first character of the current part are alphanumeric
                            if cleaned_doc[-1].isalnum() and part[0].isalnum():
                                cleaned_doc += (
                                    " "  # Add a space to prevent word merging
                                )
                        cleaned_doc += part

                    # Using file_id and file_location as a tuple to ensure uniqueness
                    file_info_key = (metadata["file_id"], metadata["file_location"])

                    # Updating the file information in the defaultdict
                    grouped_data[file_info_key]["file_id"] = metadata["file_id"]
                    grouped_data[file_info_key]["file_location"] = metadata[
                        "file_location"
                    ]
                    grouped_data[file_info_key]["file_name"] = metadata["file_name"]
                    grouped_data[file_info_key]["source"] = metadata["source"]
                    grouped_data[file_info_key]["documents"].append(
                        {id_val: cleaned_doc}
                    )

                # Convert the defaultdict to a list of dictionaries
                tool_info["files"] = list(grouped_data.values())
                tools_and_files.append(tool_info)

            print("tools_and_files", tools_and_files)

            return tools_and_files

        except Exception as e:
            print("Error while getting files:", e)
            raise e

    def delete_embedded_document_by_document_id(self, document_id: str):
        """
        This function deletes the embedded document from the collection

        Args:
            document_id: id of the document to be deleted

        """

        collection = self.persistent_client.get_collection(
            name=self.collection_name
        )
        collection.delete(ids=[document_id])

    def update_embedded_document_by_document_id(
            self, document_id: str, new_document: str
    ):
        """
        This function edits the embedded document in the collection

        Args:
            document_id: id of the document to be edited
            new_document: new document content

        """

        collection = self.persistent_client.get_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
        collection.update(ids=[document_id], documents=[new_document])

    def delete_embedding_by_tool_id(self, tool_id: int):
        """
        This function deletes the embedded document from the collection

        Args:
            tool_id: id of the tool to be deleted

        """
        collection = self.persistent_client.get_collection(
            name=self.collection_name
        )
        collection.delete(where={"tool_id": tool_id})
