import requests
import pickle
import time
import os
import re
import sys
from settings import get_settings
from langchain.utilities import GoogleSearchAPIWrapper
from agent import create_agent


"""
TODO:
- figure out how to do periodic refresh 
- figure out how to do deletion of stale articles
- how to stop searching on local dev, and load local articles instead (prevent rate limit on search engine)
    - use APP_ENV to detect local env and only perform small search as health check
    - store articles that are gitignored, but still copied into container
- setup deployment on production?
"""

os.environ["GOOGLE_CSE_ID"] = get_settings().GOOGLE_CSE_ID
os.environ["GOOGLE_API_KEY"] = get_settings().GOOGLE_API_KEY
os.environ['OPENAI_API_KEY'] = get_settings().OPENAI_API_KEY

search = GoogleSearchAPIWrapper()

LINKS_ADDR = "links"
ARTICLES_ADDR = "articles"

search_terms = [
    'Global Economy',
    'International Relations',
    'Environmental News',
    'Health Updates',
    'Technology Trends',
    'Political Movements',
    'Cultural Events',
    'Sports Highlights',
    'Space and Astronomy',
    'Human Rights',
]

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
    results = []
    for query in search_terms:
        try:
            results.extend(get_all_results(query))
        except Exception as e:
            print(e)
    print("Finished searching...")
    return results

def remove_empty_entries(lst):
    return list(filter(lambda x: x, lst))

def remove_home_pages(links):
    new_links = list(filter(lambda link: '-' in link, links))
    return new_links

def extract_articles(links, query):
    try:
        os.makedirs(ARTICLES_ADDR, exist_ok=True)
        os.makedirs(f'{ARTICLES_ADDR}/{query}', exist_ok=True)
        print(f"{len(links)} links found.\nRemoving duplicates...")
        file_links_mappings = {}
        links = list(set(links))
        print(f"{len(links)} links left.") 

        print(f'Starting newscat ---- Query: {query}')
        start_time = time.perf_counter()
        file_paths = []
        pickle_fp = f'{ARTICLES_ADDR}/file_links_mappings.pkl' 

        # Read existing mappings so existing articles don't get overwritten
        try:
            with open(pickle_fp, 'rb') as f:
                file_links_mappings = pickle.load(f)
        except:
            pass
            

        for link in links:
            hyphenated_terms = re.findall(r'\b\w+(?:-\w+)+\b', link)
            if not len(hyphenated_terms):
                continue

            title = hyphenated_terms[-1]
            file_path = f'{ARTICLES_ADDR}/{query}/{title}.txt' 
            os.system(f'newscat {link} | fmt > {file_path}')
            file_paths.append(file_path)

            try:
                with open(file_path, 'r') as f:
                    text = f.readlines()
                    if len(text) < 10:
                        os.system(f'rm {file_path}')
                        print(f"{link}...Hit paywall probably, deleted")
                    else:
                        file_links_mappings[f'{title}.txt'] = link
                        print(f"{link}...Done")
            except Exception as e:
                print("ERROR: ", e)

        with open(pickle_fp, 'wb') as f:
            pickle.dump(file_links_mappings, f)
            print("\nFile Links Mappings saved successfully to file")

        end_time = time.perf_counter()
        print(f"\n\nStatistics:")
        print(f"Total files extracted: {len(file_links_mappings)}")
        print(f"Total time taken: {end_time - start_time:0.4f} seconds")
    except Exception as e:
        print("Error:", e)

def summarise_articles():
    pass

def main(do_search=None, do_extract_articles=None):
    print("Searching for articles...")
    if do_search:
        os.makedirs(LINKS_ADDR, exist_ok=True)
        for query in search_terms:
            results = get_all_results(query)
            links = [res['link'] if 'link' in res else '' for res in results]
            links = list(set(remove_home_pages(links)))
            os.makedirs(f'{LINKS_ADDR}/{query}', exist_ok=True)
            with open(f'{LINKS_ADDR}/{query}/links.csv', 'w') as f:
                for l in links:
                    f.write(l+'\n')
    else:
        with open('links.csv', 'r') as f:
            links = f.readlines()


    if do_extract_articles:
        print("Extracting articles...")
        for query in search_terms:
            with open(f'{LINKS_ADDR}/{query}/links.csv', 'r') as f:
                links = f.readlines()
                extract_articles(links, query)

    summarise_articles()

    
if __name__ == "__main__":
    # Check the number of command line arguments
    if len(sys.argv) != 3:
        print("Usage: python main.py <arg1> <arg2>")
        print("\nArguments:")
        print("  <arg1>  - search for articles. 0 to skip, 1 to search.")
        print("  <arg2>  - extract articles found in links.csv. 0 to skip, 1 to search.")
        print("\nExamples:")
        print("  python main.py 1 1 - searches and extracts articles, and then initialize agent")
        print("  python main.py 0 0 - initialize agent directly with articles in ./articles folder")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])

