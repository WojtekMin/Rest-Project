import bs4
import re
import urllib.parse
import requests
import logging
from django.shortcuts import render
from bs4 import BeautifulSoup
from django.views.decorators.cache import cache_page

# Here I am caching scraping results for given url for 60 second * 60 * 24 which is 24 hours
@cache_page(60*60*24)
# Default view
def webpageInformation(request, url):

    # Setting up logger
    logging.basicConfig(level=logging.INFO)
    logging.info("Webpage url: {}".format(url))

    # Getting base of webpage URL
    url_base = urllib.parse.urlparse(url).netloc
    logging.info("Base of webpage url: {}" .format(url_base))

    # Getting response object, its status code and status code description
    response, response_status_code, response_status_code_description = response_getter(url)

    # Checking whether status code is greater or equal than 400 meaning that the webpage is inaccessible
    if response_status_code >= 400:
        is_reachable = False
        # Returning negative HTTP response as a rendered HTML with feedback information
        return render(request, 'webpage_information.html', {'is_reachable': is_reachable,
                                                            'response_status_code': response_status_code,
                                                            'response_status_code_description': response_status_code_description})
    else:
        is_reachable = True

    # Parsing webpage content to form that is easier to manipulate
    webpage = BeautifulSoup(response.content, "html.parser")
    # Getting webpage title
    webpage_title = webpage.title.string

    # Getting HTML version of webpage
    html_version = html_version_getter(webpage)

    # Getting number of headers of each level
    h1_headings_number, h2_headings_number, h3_headings_number, h4_headings_number, h5_headings_number, h6_headings_number = headings_calculator(
        webpage)

    # Searching and getting all links on website
    links = [link.get('href') for link in webpage.find_all('a', href=True)]

    # Initiating counters for inaccessible links and for relative url part
    inaccessible_links_number = 0
    url_relative_counter = 0

    # Calculating inaccessible links number and relative URL counter
    inaccessible_links_number, url_relative_counter = links_iteration(inaccessible_links_number, links, url_base,
                                                                      url_relative_counter)

    # Calculating total, internal and external links number
    external_links_number, internal_links_number, links_number = total_internal_external_link_calculator(links,
                                                                                                         url_base,
                                                                                                         url_relative_counter,
                                                                                                         webpage)

    # Checking if webpage contains any password or text input so that I can assume that it has login form
    is_login_form = login_form_checker(webpage)

    # Returning positive HTTP response as a rendered HTML with feedback information
    return render(request, 'webpage_information.html', {'is_reachable': is_reachable,
                                                        'response_status_code': response_status_code,
                                                        'response_status_code_description': response_status_code_description,
                                                        'webpage_title': webpage_title,
                                                        'html_version': html_version,
                                                        'h1_headings_number': h1_headings_number,
                                                        'h2_headings_number': h2_headings_number,
                                                        'h3_headings_number': h3_headings_number,
                                                        'h4_headings_number': h4_headings_number,
                                                        'h5_headings_number': h5_headings_number,
                                                        'h6_headings_number': h6_headings_number,
                                                        'links_number': links_number,
                                                        'internal_links_number': internal_links_number,
                                                        'external_links_number': external_links_number,
                                                        'inaccessible_links_number': inaccessible_links_number,
                                                        'is_login_form': is_login_form
                                                        })


# Function for checking if webpage contains any password or text input so that I can assume that it has login form
def login_form_checker(webpage):
    if len(webpage.find_all('input', {'type': 'password'})) > 0 and len(
            webpage.find_all('input', {'type': 'text'})) > 0:
        is_login_form = True
    else:
        is_login_form = False
    logging.info("Webpage has login form: {}".format(is_login_form))
    return is_login_form


# Function for getting number of headers of each level
def headings_calculator(webpage):
    h1_headings_number = len(webpage.find_all('h1'))
    h2_headings_number = len(webpage.find_all('h2'))
    h3_headings_number = len(webpage.find_all('h3'))
    h4_headings_number = len(webpage.find_all('h4'))
    h5_headings_number = len(webpage.find_all('h5'))
    h6_headings_number = len(webpage.find_all('h6'))
    return h1_headings_number, h2_headings_number, h3_headings_number, h4_headings_number, h5_headings_number, h6_headings_number


# Function for getting HTML version of webpage
def html_version_getter(webpage):
    try:
        html_version = next(item for item in webpage if isinstance(item, bs4.Doctype))
    # On some webpages there is no !DOCTYPE
    except StopIteration:
        html_version = 'No html version information'
    logging.info("HTML version: {}".format(html_version))
    return html_version


# Function for getting response object, its status code and status code description
def response_getter(url):
    response = requests.get(url)
    response_status_code = response.status_code
    response_status_code_description = response.reason
    logging.info("Requested webpage status code: {}".format(response_status_code))
    logging.info("Requested webpage status code description: {}".format(response_status_code_description))
    return response, response_status_code, response_status_code_description


# Function for calculating total, internal and external number of links
def total_internal_external_link_calculator(links, url_base, url_relative_counter, webpage):
    links_number = len(links)
    # Adding found base URL links to found relative URL links
    internal_links_number = len(
        webpage.find_all('a', {'href': re.compile('{}'.format(str(url_base)))})) + url_relative_counter
    external_links_number = links_number - internal_links_number
    logging.info("Links number: {}".format(links_number))
    logging.info("Internal links number: {}".format(internal_links_number))
    logging.info("External links number: {}".format(external_links_number))
    return external_links_number, internal_links_number, links_number


# Function for iterating through links and calculating inaccesible and relative links
def links_iteration(inaccessible_links_number, links, url_base, url_relative_counter):
    for link in links:
        if len(link) > 0:
            # Stripping relative path of leading or trailing dots for older websites compability
            link = link.strip("./")
            logging.info("Link URL: {}".format(link))

            try:
                # Using HEAD request instead of GET so that I can access only header and dont have to get the content
                resp = requests.head(link)
            # Catching exception when link is relative and does not have trailing base of URL
            except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema):
                # Constructing full URL
                logging.info("Full URL: https://" + url_base + '/' + link)
                resp = requests.head('https://' + url_base + '/' + link)
                # Incrementing counter for relative links
                url_relative_counter = url_relative_counter + 1
                logging.info("Relative path links number: {}".format(url_relative_counter))

            # Checking whether status code is greater or equal than 400 meaning that the link is inaccessible
            if resp.status_code >= 400:
                logging.info("Link response status code: {}".format(resp.status_code))
                logging.info("Link response status code description: {}".format(resp.reason))
                # Incrementing number of inaccessible links
                inaccessible_links_number = inaccessible_links_number + 1
            logging.info("Inaccessible links number: {}".format(inaccessible_links_number))
        else:
            logging.info("Link length is 0")
    return inaccessible_links_number, url_relative_counter