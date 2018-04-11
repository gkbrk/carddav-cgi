#!/usr/bin/python3
import bottle
from bottle import request, response
from bs4 import BeautifulSoup
import lxml.etree as ET
import glob
import hashlib
import random

USERNAME = 'admin'
PASSWORD = '12345'
ADDRESSBOOK_DIR = 'addressbook/'
ADDRESSBOOK_NAME = 'Leo\'s Phonebook'
SCRIPT_LOC = 'http://server.gkbrk.com/cgi-bin/carddav.py/'

def check_login(username, password):
    return username == USERNAME and password == PASSWORD

def get_contacts():
    for vcf in glob.glob(ADDRESSBOOK_DIR + '*.vcf'):
        yield (vcf.split('/')[-1], vcf)

def etag(contact):
    contact = contact.split('/')[-1]
    with open(ADDRESSBOOK_DIR + contact, 'rb') as file:
        hash = hashlib.sha1(file.read()).hexdigest()
        return '"{}"'.format(hash)

def etag_dir():
    hasher = hashlib.new('sha1')
    for _, path in get_contacts():
        with open(path, 'rb') as file:
            hasher.update(file.read())
    hash = hasher.hexdigest()
    return '"{}"'.format(hash)

@bottle.route('/', method=['PROPFIND', 'OPTIONS'])
@bottle.auth_basic(check_login)
def root():
    body = BeautifulSoup(request.body, 'xml')
    
    ms = ET.Element('{DAV:}multistatus')
    resp = ET.SubElement(ms, '{DAV:}response')
    ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC

    if body.propfind:
        props = ET.SubElement(resp, '{DAV:}propstat')
        for prop in body.propfind.find_all('prop'):
            prop = next(filter(lambda x: x.name, prop))
            if prop.name == 'current-user-principal':
                p = ET.SubElement(props, '{DAV:}prop')
                pi = ET.SubElement(p, '{DAV:}current-user-principal')
                ET.SubElement(pi, '{DAV:}href').text = 'principal'
            elif prop.name == 'addressbook-home-set':
                p = ET.SubElement(props, '{DAV:}prop')
                pi = ET.SubElement(p, '{urn:ietf:params:xml:ns:carddav}addressbook-home-set')
                ET.SubElement(pi, '{DAV:}href').text = SCRIPT_LOC + 'homeset'

    response.status = 207
    response.content_type = 'application/xml'
    return ET.tostring(ms, xml_declaration=True, encoding='utf-8')

@bottle.route('/principal/', method=['PROPFIND'])
@bottle.auth_basic(check_login)
def principal():
    body = BeautifulSoup(bottle.request.body, 'xml')

    ms = ET.Element('{DAV:}multistatus')
    resp = ET.SubElement(ms, '{DAV:}response')
    ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'principal'

    if body.propfind:
        props = ET.SubElement(resp, '{DAV:}propstat')
        for prop in body.propfind.find_all('prop'):
            prop = next(filter(lambda x: x.name, prop))
            if prop.name == 'addressbook-home-set':
                p = ET.SubElement(props, '{DAV:}prop')
                pi = ET.SubElement(p, '{urn:ietf:params:xml:ns:carddav}addressbook-home-set')
                ET.SubElement(pi, '{DAV:}href').text = SCRIPT_LOC + 'homeset'

    response.status = 207
    response.content_type = 'application/xml'
    return ET.tostring(ms, xml_declaration=True, encoding='utf-8')

@bottle.route('/homeset/', method=['PROPFIND'])
@bottle.auth_basic(check_login)
def homeset():
    ms = ET.Element('{DAV:}multistatus')

    resp = ET.SubElement(ms, '{DAV:}response')
    ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'homeset'

    props = ET.SubElement(resp, '{DAV:}propstat')
    p = ET.SubElement(props, '{DAV:}prop')

    pi = ET.SubElement(p, '{DAV:}resourcetype')
    ET.SubElement(pi, '{DAV:}collection')

    resp = ET.SubElement(ms, '{DAV:}response')
    ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'addressbook'

    props = ET.SubElement(resp, '{DAV:}propstat')
    p = ET.SubElement(props, '{DAV:}prop')

    pi = ET.SubElement(p, '{DAV:}resourcetype')
    ET.SubElement(pi, '{DAV:}collection')
    ET.SubElement(pi, '{urn:ietf:params:xml:ns:carddav}addressbook')

    ET.SubElement(p, '{DAV:}displayname').text = ADDRESSBOOK_NAME

    response.status = 207
    response.content_type = 'application/xml'
    return ET.tostring(ms, xml_declaration=True, encoding='utf-8')

@bottle.route('/addressbook/', method=['PROPFIND'])
@bottle.auth_basic(check_login)
def addressbook():
    body = BeautifulSoup(request.body, 'xml')

    ms = ET.Element('{DAV:}multistatus')
    resp = ET.SubElement(ms, '{DAV:}response')
    ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'addressbook/'

    if body.propfind:
        props = ET.SubElement(resp, '{DAV:}propstat')

        p = ET.SubElement(props, '{DAV:}prop')
        pi = ET.SubElement(p, '{DAV:}resourcetype')
        ET.SubElement(pi, '{DAV:}collection')
        ET.SubElement(pi, '{urn:ietf:params:xml:ns:carddav}addressbook')

        ET.SubElement(props, '{DAV:}status').text = 'HTTP/1.1 200 OK'
        
        ET.SubElement(p, '{DAV:}getetag').text = etag_dir()
        ET.SubElement(p, '{http://calendarserver.org/ns/}getctag').text = etag_dir()

        ET.SubElement(p, '{DAV:}displayname').text = ADDRESSBOOK_NAME
        ET.SubElement(p, '{urn:ietf:params:xml:ns:carddav}addressbook-description').text = ADDRESSBOOK_NAME
        
    for contact, contact_path in get_contacts():
        resp = ET.SubElement(ms, '{DAV:}response')
        ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'addressbook/' + contact
        props = ET.SubElement(resp, '{DAV:}propstat')
        p = ET.SubElement(props, '{DAV:}prop')
        ET.SubElement(props, '{DAV:}status').text = 'HTTP/1.1 200 OK'

        ET.SubElement(p, '{DAV:}resourcetype')
        ET.SubElement(p, '{DAV:}getcontenttype').text = 'text/vcard; charset=utf-8'
        ET.SubElement(p, '{DAV:}getetag').text = etag(contact)

    response.status = 207
    response.content_type = 'application/xml'
    return ET.tostring(ms, xml_declaration=True, encoding='utf-8')

@bottle.route('/addressbook/', method=['REPORT'])
@bottle.auth_basic(check_login)
def contact():
    body = BeautifulSoup(request.body, 'xml')
    ms = ET.Element('{DAV:}multistatus')

    for target in body.find_all('href'):
        contact = target.text.split('/')[-1]
        resp = ET.SubElement(ms, '{DAV:}response')
        ET.SubElement(resp, '{DAV:}href').text = SCRIPT_LOC + 'addressbook/' + contact

        props = ET.SubElement(resp, '{DAV:}propstat')
        p = ET.SubElement(props, '{DAV:}prop')
        ET.SubElement(p, '{DAV:}getetag').text = etag(contact)
        ET.SubElement(p, '{DAV:}getctag').text = etag(contact)
        with open(ADDRESSBOOK_DIR + contact, 'rb') as file:
            contents = file.read().decode('utf-8')
            ET.SubElement(p, '{urn:ietf:params:xml:ns:carddav}address-data').text = contents

    response.status = 207
    response.content_type = 'application/xml'
    return ET.tostring(ms, xml_declaration=True, encoding='utf-8')

@bottle.route('/addressbook/<path>', method=['GET'])
@bottle.auth_basic(check_login)
def contact_get(path):
    response.set_header('ETag', etag(path))
    response.content_type = 'text/vcard'
    with open(ADDRESSBOOK_DIR + path, 'rb') as contact_file:
        return contact_file.read()

@bottle.route('/addressbook/<path>', method=['PUT'])
@bottle.auth_basic(check_login)
def contact_put(path):
    with open(ADDRESSBOOK_DIR + path, 'wb+') as contact_file:
        contact_file.write(request.body.read())
    response.status = 201

bottle.run(server='cgi', debug=True)
