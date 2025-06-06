import ollama
import os
import datetime

from langchain_community.document_loaders import PDFPlumberLoader

model = "llama3.2"

pdf_files = [f for f in os.listdir("./data") if f.endswith(".pdf")]

all_pages = []

for pdf_file in pdf_files:

    file_path = os.path.join("./data", pdf_file)
    print(f"Processing PDF file: {pdf_file}")

    # Load the PDF file
    loader = PDFPlumberLoader(file_path=file_path)
    pages = loader.load_and_split()
    print(f"pages length: {len(pages)}")

    all_pages.extend(pages)

  
    text = pages[0].page_content
    print(f"Text extracted from the PDF file '{pdf_file}':\n{text}\n")

    prompt = f"""
    You are an AI assistant that helps with summarizing PDF documents.
    
    Here is the content of the PDF file '{pdf_file}':
    
    {text}
    
    Please summarize the content of this document in a few sentences.
    """

   
    try:
        response = ollama.generate(model=model, prompt=prompt)
        summary = response.get("response", "")

        
    except Exception as e:
        print(
            f"An error occurred while summarizing the PDF file '{pdf_file}': {str(e)}"
        )


from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)

text_chunks = []
for page in all_pages:
    chunks = text_splitter.split_text(page.page_content)
    text_chunks.extend(chunks)

print(f"Number of text chunks: {text_chunks}")



def add_metadata(chunks, doc_title):
    metadata_chunks = []
    for chunk in chunks:
        metadata = {
            "title": doc_title,
            "author": "US Business Bureau",  # Update based on document data
            "date": str(datetime.date.today()),
        }
        metadata_chunks.append({"text": chunk, "metadata": metadata})
    return metadata_chunks



metadata_text_chunks = add_metadata(text_chunks, "BOI US FinCEN")




ollama.pull("nomic-embed-text")


def generate_embeddings(text_chunks, model_name="nomic-embed-text"):
    embeddings = []
    for chunk in text_chunks:
        # Generate the embedding for each chunk
        embedding = ollama.embeddings(model=model_name, prompt=chunk)
        embeddings.append(embedding)
    return embeddings



texts = [chunk["text"] for chunk in metadata_text_chunks]
embeddings = generate_embeddings(texts)




from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_ollama import OllamaEmbeddings

docs = [
    Document(page_content=chunk["text"], metadata=chunk["metadata"])
    for chunk in metadata_text_chunks
]

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

fastembedding = FastEmbedEmbeddings()

vector_db_path = "./db/vector_db"

vector_db = Chroma.from_documents(
    documents=docs,
    embedding=fastembedding,
    persist_directory=vector_db_path,
    
    collection_name="docs-local-rag",
)



from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers.multi_query import MultiQueryRetriever

local_model = "llama3.2"
llm = ChatOllama(model=local_model)

QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""You are an AI language model assistant. Your task is to generate five
    different versions of the given user question to retrieve relevant documents from
    a vector database. By generating multiple perspectives on the user question, your
    goal is to help the user overcome some of the limitations of the distance-based
    similarity search. Provide these alternative questions separated by newlines.
    Original question: {question}""",
)


retriever = MultiQueryRetriever.from_llm(
    vector_db.as_retriever(), llm, prompt=QUERY_PROMPT
)


template = """Answer the question based ONLY on the following context:
{context}
Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)


chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

questions = """
by when should I file if my business was established in 2013?"""
print((chain.invoke(questions)))
response = chain.invoke(questions)


from elevenlabs.client import ElevenLabs
from elevenlabs import play
from elevenlabs import stream
from dotenv import load_dotenv

load_dotenv()

text_response = response

api_key = os.getenv("ELEVENLABS_API_KEY")


client = ElevenLabs(api_key=api_key)
audio_stream = client.generate(text=text_response, model="eleven_turbo_v2", stream=True)

stream(audio_stream)
