import json
import os
from uuid import UUID, uuid4

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="src/static"), name="static")

cars = []


class Photo(BaseModel):
    img_url: str


class Car(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    vin: str
    brand: str
    model: str
    production_year: int
    color: str
    short_description: str = Field(max_length=100)
    photos: list[Photo] | None = None
    price: int | None = None


def load_cars_from_json(file_path: str):
    global cars
    with open(file_path, encoding="utf-8") as file:
        cars_data = json.load(file)
        cars = [
            Car(
                id=str(car.get("id")),
                vin=str(car.get("vin")),
                brand=str(car.get("brand")),
                model=str(car.get("model")),
                production_year=int(str(car.get("production_year"))),
                color=str(car.get("color")),
                short_description=str(car.get("short_description")),
                photos=[
                    Photo(img_url=photo.get("img_url")) for photo in car.get("photos")
                ],
                price=int(
                    str(car.get("price")),
                ),
            )
            for car in cars_data
        ]


# Load cars from JSON file on startup
json_file_path = os.path.join(os.path.dirname(__file__), "data", "cars.json")
photos_dir = os.path.join(os.path.dirname(__file__), "static")
load_cars_from_json(json_file_path)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/cars", response_class=HTMLResponse)
async def list_cars(request: Request):
    load_cars_from_json(json_file_path)
    return templates.TemplateResponse(
        request=request, name="cars.html", context={"cars": cars}
    )


@app.get("/car-details/{car_id}", response_class=HTMLResponse)
async def car_details(request: Request, car_id: UUID):
    car = next((car for car in cars if car.id == car_id), None)
    if car:
        return templates.TemplateResponse(
            "details.html", {"request": request, "car": car}
        )
    return HTMLResponse(content="Car not found", status_code=404)


@app.get("/add-car", response_class=HTMLResponse)
async def get_add_car_form(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})


@app.post("/add-car", response_class=HTMLResponse)
async def add_car(
    request: Request,
    photos: list[UploadFile],
    vin: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    production_year: int = Form(...),
    color: str = Form(...),
    short_description: str = Form(...),
    price: int = Form(...),
):
    photo_urls: list = []

    car = Car(
        vin=vin,
        brand=brand,
        model=model,
        production_year=production_year,
        color=color,
        short_description=short_description,
        price=price,
    )

    if photos:
        for file in photos:
            photo_path = f"{photos_dir}/{car.id}-{file.filename}"
            with open(photo_path, "wb+") as f:
                f.write(file.file.read())
            photo_urls.append(Photo(img_url=f"{car.id}-{file.filename}"))

    car.photos = photo_urls
    cars.append(car.model_dump())

    with open(json_file_path, "w", encoding="utf-8") as file:
        json.dump(jsonable_encoder(cars), file, ensure_ascii=False, indent=4)

    load_cars_from_json(json_file_path)

    return templates.TemplateResponse("cars.html", {"request": request, "cars": cars})


@app.delete("/delete-car/{car_id}", response_class=HTMLResponse)
async def delete_car(car_id: str, request: Request):
    load_cars_from_json(json_file_path)
    global cars
    car = next((car for car in cars if car.id == UUID(car_id)), None)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")

    cars = [car for car in cars if car.id != UUID(car_id)]

    with open(json_file_path, "w", encoding="utf-8") as file:
        json.dump(jsonable_encoder(cars), file, ensure_ascii=False, indent=4)

    for filename in os.listdir(photos_dir):
        if car_id in filename:
            file_path = os.path.join(photos_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    return templates.TemplateResponse("cars.html", {"request": request, "cars": cars})
