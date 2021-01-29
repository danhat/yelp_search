
# Yelp Search


import time, json, requests
from bs4 import BeautifulSoup

# import config




"""
  Read the Yelp API key from file

  Args:
    filepath (string): file containing API Key
  Returns:
    api_key (string): Yelp API key for authentication
"""
def read_api_key(filepath):
  with open(filepath, 'r') as f:
    return f.read().replace('\n','')




"""
  Return the raw HTML at the specified URL.

  Args:
    url (string): URL to get html code from

  Returns:
    status_code (integer): status of the request (200: successful, 404: not found)
    raw_html (string): the raw HTML content of the response, properly encoded according to the HTTP headers.
"""
def retrieve_html(url):
  response = requests.get(url)
  status_code = response.status_code
  raw_html = response.text
  return status_code, raw_html



"""
  Send a HTTP GET request and return a json response

  Args:
    url (string): API endpoint url
    headers (dict): A python dictionary containing HTTP headers including authentication to be sent
    url_params (dict): The parameters (required and optional) supported by endpoint

  Returns:
    content_json (dictionary): response from request as dictionary
"""
def api_get_request(url, headers, url_params):
  http_method = 'GET'
  # send request and store results (Response object) in response
  response = requests.get(url, params = url_params, headers = headers)
  # get response as dictionary
  content_json = response.json()
  return content_json



"""
  Get and return parameters needed for sending an HTTP GET requests

  Args:
    url_addition(string): ending of Yelp API endpoint URL
    api_key(string): Yelp API key for authentication
    **kwargs: additional arguments needed pulling data from api

  Returns:
    (list): list of tuple
      url(string): API endpoint URL
      headers(dict): headers needed for accessing the Yelp API
      url_params(dict): other parameters needing for getting data (such as location, restaurant name, etc.)
"""
def get_url_params(url_addition, api_key, **kwargs):
  # url endpoint for search + url addition (for search all businesses, search reviews of certain business, etc)
  url = 'https://api.yelp.com/v3/businesses' + url_addition

  # authentication
  headers = {'Authorization': f"Bearer {api_key}"}

  url_params = {}

  # include keyword arguments in url_params
  if kwargs is not None:
    for key, value in kwargs.items():
      url_params[f'{key}'] = value

  return url, headers, url_params






"""
  Get at most 20 businesses based on location.

  Args:
    api_key (string): Yelp API key for authentication
    location (string): business Location
    offset (int): parameter for pagination

  Returns:
    total (integer): total number of businesses on Yelp corresponding to the location
    businesses (list): list representing each business
"""
def yelp_search(api_key, location, offset = 0):
  # get url, headers, and URL parameters for request
  url, headers, url_params = get_url_params('/search', api_key, location = location, offset = offset)

  # send request and get results as a dictionary
  response_json = api_get_request(url, headers, url_params)
  return response_json["total"], list(response_json["businesses"])




"""
  Returns a list of tuples (url, headers, url_params) for paginated search of all restaurants.
  Paginated to stop timeout due to too many Yelp API requests.

  Args:
    api_key (string): Yelp API key for authentication
    location (string): Business Location
    total (int): Total number of items to be fetched

  Returns:
    results (list): list of tuple (url, headers, url_params)
"""
def paginated_restaurant_search_requests(api_key, location, total):
  pages = [] # add result to pages

  current_offset = 0
  while current_offset < total:
    url, headers, url_params = get_url_params('/search', api_key, location, offset = current_offset, limit = 20, categories = "restaurants")
    pages.append((url, headers, url_params))
    current_offset = current_offset + 20
    # slight pause to stop too many requests to Yelp API
    time.sleep(.3)

  return pages




"""
  Construct the pagination requests for ALL the restaurants on Yelp for a given location.

  Args:
    api_key (string): Yelp API key for authentication
    location (string): Business Location

  Returns:
    results (list): list of dicts representing each restaurant in passed location
"""
def all_restaurants(api_key, loc):

  # offset passed to get first page of restaurants in Yelp
  url, headers, url_params = get_url_params('/search', api_key, location = loc, offset = 0)

  # get results from request
  content_json = api_get_request(url, headers, url_params)
  total_items = content_json["total"]
  # get parameters needed to retrieve all restaurants in the given location
  restaurant_pages = paginated_restaurant_search_requests(api_key, loc, total_items)

  # use returned list of (url, headers, url_params) and function api_get_request to retrive all restaurants
  result = []
  for i in range(len(restaurant_pages)):
    page = restaurant_pages[i]

    url = page[0]
    headers = page[1]
    url_params = page[2]

    # send request
    content_json = api_get_request(url, headers, url_params)
    page_data = content_json['businesses']

    for j in range(len(page_data)):
      result.append(page_data[j])

    # pause slightly after each request to prevent timeout
    time.sleep(.3)

  return result



"""
  Get the ID of a business from the Yelp API (https://www.yelp.com/developers/documentation/v3/business_match)

  Args:
    api_key(string): Yelp API key for authentication
    name(string): name of the business to access
    address(string): address of the business to access (can be empty if business has no address)
    city(string): city of the business to access
    state(string): ISO 3166-2 state code of the wanted business
    country(string): ISO 3166-1 alpha-2 country code of the wanted business

  Return:
    (string): business id
    or None if there is a validation error
"""
def get_business_id(api_key, name, address, city, state, country):
  url, headers, url_params = get_url_params('/matches', api_key, name = name, address1 = address, city = city, state = state, country = country)

  response_json = api_get_request(url, headers, url_params)
  
  if 'error' in response_json:
    print('error code:', (response_json['error'])['code'])
    print('description:', (response_json['error'])['description'])
    return None
  
  business = response_json['businesses']
  return (business[0])['id']



"""
  Get three reviews from Yelp API

  Args:
    api_key(string): Yelp API key for authentication
    name(string): name of the business to access
    address(string): address of the business to access (can be empty if business has no address)
    city(string): city of the business to access
    state(string): ISO 3166-2 state code of the wanted business
    country(string): ISO 3166-1 alpha-2 country code of the wanted business

  Returns:
    reviews(dict): reviews
    total(int): total number of reviews
    
    or None if business is not found
"""
def extract_reviews(api_key, name, address, city, state, country):
  business_id = get_business_id(api_key, name, address, city, state, country)
  
  if business_id == None:
    print('business not found')
    return None

  # add business_id to endpoint
  url_addition = '/' + business_id + '/reviews'
  url, headers, url_params = get_url_params(url_addition, api_key)

  response_json = api_get_request(url, headers, url_params)

  reviews = response_json['reviews']
  total = response_json['total']
  return reviews, total






"""
  Parse Yelp API results to extract restaurant URLs.

  Args:
    data (string): string of properly formatted JSON.

  Returns:
    (list): list of URLs as strings from the input JSON.
"""
"""
  url, headers, url_params = location_search_params(api_key, "Chicago", offset=0)
  response = requests.get(url, params = url_params, headers = headers)
  response_json = response.json()
  response_str = json.dumps(response_json)
  parsed = parse_api_response(response_str)
  print(parsed[1:5])
"""
def parse_api_response(data):

  data_ = json.loads(data)
  data_ = data_['businesses']

  urls = []
  for i in range(len(data_)):
    temp = data_[i]
    urls.append(temp['url'])

  return urls






"""
  Parse the reviews on a single page of a restaurant using BS4.
  Created due to only being able access 3 reviews per restaurant from Yelp Fusion.
  **No longer functional due to not being able to access yelp reviews html(??)**

  Args:
    html (string): string of HTML corresponding to a Yelp restaurant

  Returns:
    tuple(list, string): a tuple of two elements
      first element: list of dictionaries corresponding to the extracted review information
      second element: URL for the next page of reviews (or None if it is the last page)
"""
def parse_page(html):

  soup = BeautifulSoup(html,'html.parser')

  #f = open('soup_html.html', 'w')
  #f.write(soup.prettify())
  #f.close()

  url_next = soup.find('link', rel='next')
  if url_next:
    url_next = url_next.get('href')
  else:
    url_next = None


  reviews = soup.find_all('div', itemprop='review')
  reviews_list = []

  for i in range(len(reviews)):
    r = reviews[i]
    author = r.find(itemprop='author')
    author = author.attrs['content']
    rating = r.find(itemprop='ratingValue')
    rating = float(rating.attrs['content'])
    date = r.find(itemprop='datePublished')
    date = date.attrs['content']
    description = r.find('p').text
    #description = r.find(itemprop='description')
    #description = description.attrs['p']
    review = {'author': author, 'rating': rating, 'date': date, 'description': description}
    reviews_list.append(review)


  return reviews_list, url_next





"""
  Retrieve ALL of the reviews for a single restaurant on Yelp.
  Created due to only being able access 3 reviews per restaurant from Yelp Fusion.
  **No longer functional due to not being able to access yelp reviews html(??)**

  Parameters:
    url (string): Yelp URL corresponding to the restaurant of interest.

  Returns:
    reviews (list): list of dictionaries containing extracted review information
"""
def extract_reviews_via_html(url):

  code, html = retrieve_html(url)
  reviews, next_url = parse_page(html)
  while (next_url != None):
    code, html = retrieve_html(next_url)
    reviews_temp, next_url_temp = parse_page(html)
    for r in reviews_temp:
      reviews.append(r)
    next_url = next_url_temp

  return reviews




def main():
  api_key = read_api_key('yelp_api_key.txt')

  #all_rest = all_restaurants(api_key, 'Homewood Illinois')

  #url = 'https://www.yelp.com/biz/the-jibarito-stop-chicago-2'
  reviews, total = extract_reviews(api_key, 'jibarito shop', '1646 W 18th St', 'Chicago', 'IL', 'US')
  print(len(reviews))




if __name__ == '__main__':
  main()
