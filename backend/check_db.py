from app.database.connection import db_manager
from app.models.hot_place import HotPlace
from sqlalchemy import func

def check_hot_places():
    db = db_manager.get_session()
    try:
        count = db.query(HotPlace).count()
        print(f"Total HotPlaces: {count}")
        
        places = db.query(HotPlace).limit(5).all()
        for p in places:
            print(f"ID: {p.id}, Name: {p.name}, ImagePath: '{p.image_path}', Adress: '{p.adress}'")
            
        with_img = db.query(HotPlace).filter(HotPlace.image_path.isnot(None), HotPlace.image_path != "").count()
        print(f"HotPlaces with non-empty image_path: {with_img}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_hot_places()
