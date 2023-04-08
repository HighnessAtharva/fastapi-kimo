import contextlib
from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

app = FastAPI()
client = MongoClient('mongodb://localhost:27017/')
db = client['courses']


"""
Endpoint to get a list of all available courses. This endpoint needs to support 3 modes of
sorting: Alphabetical (based on course title, ascending), date (descending) and total course
rating (descending). Additionaly, this endpoint needs to support optional filtering of courses
based on domain.
"""
@app.get('/courses')
def get_courses(sort_by: str = 'date', domain: str = None):
    # set the rating.total and rating.count to all the courses based on the sum of the chapters rating
    for course in db.courses.find():
        total = 0
        count = 0
        for chapter in course['chapters']:
            with contextlib.suppress(KeyError):
                total += chapter['rating']['total']
                count += chapter['rating']['count']
        db.courses.update_one({'_id': course['_id']}, {'$set': {'rating': {'total': total, 'count': count}}})



    # sort_by == 'date' [DESCENDING]
    if sort_by == 'date':
        sort_field = 'date'
        sort_order = -1

    # sort_by == 'rating' [DESCENDING]
    elif sort_by == 'rating':
        sort_field = 'rating.total'
        sort_order = -1

    # sort_by == 'alphabetical' [ASCENDING]
    else:  
        sort_field = 'name'
        sort_order = 1

    query = {}
    if domain:
        query['domain'] = domain


    courses = db.courses.find(query, {'name': 1, 'date': 1, 'description': 1, 'domain':1,'rating':1,'_id': 0}).sort(sort_field, sort_order)
    return list(courses)
 
 
"""
Endpoint to get the course overview. 
"""
@app.get('/courses/{course_id}')
def get_course(course_id: str):
    course = db.courses.find_one({'_id': ObjectId(course_id)}, {'_id': 0, 'chapters': 0})
    if not course:
        raise HTTPException(status_code=404, detail='Course not found')
    try:
        course['rating'] = course['rating']['total']
    except KeyError:
        course['rating'] = 'Not rated yet' 
    
    return course
 

""" 
Endpoint to get a specific chapter information.
""" 
@app.get('/courses/{course_id}/{chapter_id}')
def get_chapter(course_id: str, chapter_id: str):    
    course = db.courses.find_one({'_id': ObjectId(course_id)}, {'_id': 0, })
    if not course:
        raise HTTPException(status_code=404, detail='Course not found')
    chapters = course.get('chapters', [])
    try:
        chapter = chapters[int(chapter_id)]
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=404, detail='Chapter not found') from e
    return chapter


# Endpoint to allow users to rate each chapter (positive/negative) 1 for Positive, -1 For Negative, while aggregating all ratings for each course.
@app.post('/courses/{course_id}/{chapter_id}')
def rate_chapter(course_id: str, chapter_id: str, rating: int = Query(..., gt=-2, lt=2)):
    course = db.courses.find_one({'_id': ObjectId(course_id)}, {'_id': 0, })
    if not course:
        raise HTTPException(status_code=404, detail='Course not found')
    chapters = course.get('chapters', [])
    try:
        chapter = chapters[int(chapter_id)]
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=404, detail='Chapter not found') from e
    try:
        chapter['rating']['total'] += rating
        chapter['rating']['count'] += 1
    except KeyError:
        chapter['rating'] = {'total': rating, 'count': 1}
    db.courses.update_one({'_id': ObjectId(course_id)}, {'$set': {'chapters': chapters}})
    return chapter 


