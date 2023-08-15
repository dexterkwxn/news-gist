import os
import pickle
import time
import re
import uvicorn
import httpx

from pyngrok import ngrok
from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from typing import Annotated

from glob import glob
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT

# https://programmablesearchengine.google.com/controlpanel/create
# os.environ["GOOGLE_CSE_ID"] = "945ae6615cc4a4b11"
# os.environ["GOOGLE_CSE_ID"] = "0300d9105ab254ee7"
os.environ["GOOGLE_CSE_ID"] = "371d2bec4b2f44a56"

# https://console.cloud.google.com/apis/credentials
# os.environ["GOOGLE_API_KEY"] = "AIzaSyBx3WIrMrRnc6aH0zqa9CVeSmhjrqBSq2g"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyDgpM9XFush5IBs6OQtcUPjJOuS6pIHgJw"
os.environ["GOOGLE_API_KEY"] = "AIzaSyCQkqoKMhN8JtEyUxcH3FkVZQNeWoqOEPY"

os.environ['OPENAI_API_KEY'] = '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'

search = GoogleSearchAPIWrapper()

global qa
global file_links_mappings
 
def get_results_on_page(page):
    if page < 1:
        page = 1
    search_params = {
        'sort': 'date',
        'start': str(1 + 10*(page-1)),
        'excludeTerms': 'promo discount',
    }
    def get_results(query):
        return search.results(query, 10, search_params)
    return get_results

def get_all_results(query):
    results = []
    try:
        for i in range(1): # number of pages of search term
            results.extend(get_results_on_page(i+1)(query))
    except Exception as e:
        print(e)
    return results

def search_all_terms():
    search_terms = [
        'Carbon market news',
#        'Environmental news updates',
#        'Climate change market developments',
#        'Renewable energy market updates',
#        'Carbon pricing developments',
#        'Environmental policy news',
#        'Clean technology',
#        'Carbon offset market news',
#        'ESG (Environmental, Social, and Governance) updates',
#        'Sustainable development news',
    ]
    results = []
    for query in search_terms:
        try:
            results.extend(get_all_results(query))
        except Exception as e:
            print(e)
    return results

def remove_empty_entries(lst):
    return list(filter(lambda x: x, lst))

def remove_home_pages(links):
    new_links = list(filter(lambda link: '-' in link, links))
    return new_links

def text_is_relevant(text):
    keywords = [
            'carbon',
            'methodology',
            'sustainability',
            'renewable',
            'emissions',
            'greenhouse',
            'clean energy',
            'sequestration',
            'enviroment',
            'ecological',
            'climate',
            'esg',
            ]
    for keyword in keywords:
        for line in text:
            if keyword in line.lower():
                return True
    return False

def extract_articles(links):
    global file_links_mappings
    try:
        print(f"{len(links)} links found.\nRemoving duplicates...")
        file_links_mappings = {}
        links = list(set(links))
        print(f"{len(links)} links left.") 

        print('Starting newscat...')
        start_time = time.perf_counter()
        for link in links:
            print(f'{link}... ', end='')
            hyphenated_terms = re.findall(r'\b\w+(?:-\w+)+\b', link)
            #split_link = link.split(sep="/")
            #title = split_link[-2] if split_link[-1] == "" else split_link[-1]
            title = hyphenated_terms[-1]
            file_path = f'articles/{title}.txt'
            os.system(f'newscat {link} | fmt > {file_path}')

            try:
                with open(file_path, 'r') as f:
                    text = f.readlines()
                    if len(text) < 10:
                        os.system(f'rm {file_path}')
                        print("Hit paywall, deleted")
                    elif text_is_relevant(text):
                        file_links_mappings[f'{title}.txt'] = link
                        print("Done")
                    else:
                        os.system(f'rm {file_path}')
                        print("Not relevant")
            except Exception as e:
                print("ERROR: ", e)

        with open('articles/file_links_mappings.pkl', 'wb') as f:
            pickle.dump(file_links_mappings, f)
            print("\nFile Links Mappings saved successfully to file")

        end_time = time.perf_counter()
        print(f"\n\nStatistics:")
        print(f"Total files extracted: {len(file_links_mappings)}")
        print(f"Total time taken: {end_time - start_time:0.4f} seconds")
    except Exception as e:
        print("Error:", e)

def get_sources(response):
    global file_links_mappings
    sources = []
    for source in response['source_documents']:
        sources.append(source.metadata['source'])

    sources = list(set(map(lambda source: re.findall(r'\b\w+(?:-\w+)+\b', source)[-1], sources)))

    source_text = "Source(s):\n"
    for source in sources:
        try:
            source_text += file_links_mappings[f'{source}.txt']
            source_text += '\n'
        except KeyError as e:
            print(f"KeyError: file not in file_links_mapping - {e}")
    return source_text

def get_response(query, chat_history):
    global file_links_mappings
    vectordbkwargs = {"search_distance": 0.8}
    response = qa({'question': query, 'chat_history': chat_history, "vectordbkwargs": vectordbkwargs})
    return response['answer'] + '\n\n' + get_sources(response)


def main(do_search=None, do_extract_articles=None):
    global qa
    global file_links_mappings
    if do_search:
        print("Searching for articles...")
        results = search_all_terms()
        links = [res['link'] if 'link' in res else '' for res in results]
        links = list(set(remove_home_pages(links)))
        with open('links.csv', 'w') as f:
            for l in links:
                f.write(l+'\n')
    else:
        with open('links.csv', 'r') as f:
            links = f.readlines()

    if do_extract_articles:
        print("Extracting articles...")
        extract_articles(links)

    print("Reading saved articles...")
    articles = glob("articles/*.txt")

    with open('articles/file_links_mappings.pkl', 'rb') as f:
        file_links_mappings = pickle.load(f)
    
    print("Splitting texts...")
    texts = []
    for article in articles:
        loader = TextLoader(article)
        document = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        text = text_splitter.split_documents(document)
        texts.extend(text)

    print("Generating Embeddings...")
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(texts, embeddings)

    llm = OpenAI(temperature=0)

    qa = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(temperature=0, model='gpt-3.5-turbo'),
        vectorstore.as_retriever(),
        return_source_documents=True,
        verbose=True,
        )
    print("Chain created.")
    return qa
    

def lambda_handler(event, context):
    res = main(1, 1)
    return {
        'message': res
    }

