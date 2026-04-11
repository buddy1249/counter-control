from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse  
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Annotated, Literal
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app_env = os.getenv("APP_ENV", "development")

app = FastAPI(
    docs_url=None if app_env == "production" else "/docs",
    redoc_url=None if app_env == "production" else "/redoc",
    openapi_url=None if app_env == "production" else "/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"], # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"], # Разрешить все заголовки
)

differential_value = ['Error', 'Error']

class CheckShema(BaseModel):
    """Валидация полей формы в сочетании с аннотациями типов Python 
       (на базе Pydantic Validation). Настройка ограничений для обеспечения автоматической 
       проверки данных перед обработкой"""
    name_counter: Literal['g16', 'g25', 'g40', 'g65', 'g160'] # только данные наименования
    Dy: float = Field(ge=0, le=300) # ограничение диаметра трубопровода
    actual_pressure: float = Field(ge=0, le=0.8) # ограничение давления
    consumption_hour: float
    pressure_drop: float = Field(ge=0) # ограничение для перепада давления
    gas_density: float = Field(ge=0.66, le=0.97) # ограничение дапазона плотности

    @field_validator('consumption_hour')
    @classmethod    
    def validate_price_by_category(cls, v: float, info: ValidationInfo):
        """Валидация поля формы 'consumption_hour', значение которого зависит от модели счетчика
           поле 'name_counter' (для каждой модели свой максимальный изм. расход Qmax)"""        
        name_counter = info.data.get('name_counter')
        if name_counter == 'g16' and v > 25:
            raise ValueError('Расход (рабочий) газа для g16 не может превышать Qmax = 25 м3/ч')
        if name_counter == 'g25' and v > 40:
            raise ValueError('Расход (рабочий) газа для g25 не может превышать Qmax = 40 м3/ч')
        if name_counter == 'g40' and v > 65:
            raise ValueError('Расход (рабочий) газа для g40 не может превышать Qmax = 65 м3/ч')
        if name_counter == 'g65' and v > 100:
            raise ValueError('Расход (рабочий) газа для g65 не может превышать Qmax = 100 м3/ч')
        if name_counter == 'g160' and v > 250:
            raise ValueError('Расход (рабочий) газа для g160 не может превышать Qmax = 250 м3/ч')
        return v


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Вместо стандартной ошибки 422 возвращаем страницу с деталями"""
    errors = exc.errors()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "differential_value": differential_value,
        "errors": errors, # Передаем список ошибок в шаблон
        "error_msg": """Проверьте правильность ввода данных (числа должны быть числами).
                        Dy - диаметн не должен превышать 300. Счетчики только модели:  g16, g25, g40, g65, g160 
                        consumption_hour - рабочий расход не должен превышать максимального для данного счетчика
                        gas_density - плотность газа должна быть в пределах [0.66....0.97]"""
    })


templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


""" Константные значения для расчетного перепада давления """
RHOcp = 1.29 # плотность константное значение согласно методики
Pp = 0.1 # давление константное значение согласно методики


@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    """
    Вызов метода который рендерит и возвращает HTML-шаблон 
    (main.html) для ввода данных
    """
    return templates.TemplateResponse("main.html", {"request": request})


@app.post("/submit")    
async def handle_form(request: Request, user: Annotated[CheckShema, Form()]):
    """
    Обработка запроса, расчет параметров и отправка пользователю HTML-страницы index.html 
    с данными и визуализацией характеризующими состояние оборудования """
   
    if user.name_counter == 'g16':
        counter_params = [25, 100] # Паспортные характеристики счетчиков (max Q, max DP)
    elif user.name_counter == 'g25':
        counter_params = [40, 150]
    elif user.name_counter == 'g40':
        counter_params = [65, 300]
    elif user.name_counter == 'g65':
        counter_params = [100, 450]
    elif user.name_counter == 'g160':
        counter_params = [250, 620]
        
    """ Расчет перепад давления на счетчике в зависимости от расхода """
    DPp = counter_params[1] * ((user.consumption_hour / counter_params[0]) ** 2)


    """ Расчет контрольного значения перепада давления для конкретных рабочих
        условий в соответствие с ГОСТ Р8.740 – 2011 """
    DP = round(DPp * ((user.gas_density * user.actual_pressure) / (RHOcp * Pp)), 1)     

    if user.pressure_drop <= 1.2 * DP:        
        differential_value = ["DP_изм <= 1.2 * DP_расч", "Счетчик газа работоспособен"]    
    elif 1.2 * DP <= user.pressure_drop <= 1.5 * DP:        
        differential_value = ["1.2 * DP_расч <= DP_изм <= 1.5 * DP_расч", """Необходимо обратить на этот счетчик особое
            внимание, так как возможно скоро он будет нуждаться в обслуживании или ремонте"""]
    elif 1.5 * DP <= user.pressure_drop <= 1.8 * DP:        
        differential_value = ["1.5 * DP_расч <= DP_изм <= 1.8 * DP_расч", """Необходимо провести
            дополнительный контроль перепада давления на
            счетчике через небольшой промежуток времени (3-
            5 дней): если перепад на счетчике газа не
            уменьшился, то принять решение о необходимости
            проведения технического обслуживания или
            ремонта счетчика; если перепад на счетчике
            вернулся в границы допустимых значений, то
            счетчик считается работоспособным"""]
    elif user.pressure_drop >= 1.8 * DP:        
        differential_value = ["DP_изм >= 1.8 * DP_расч", """Счетчик газа требует технического обслуживания
            или ремонта """ ]
    else:
        differential_value = ['Error', 'Error']    

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "name_counter": user.name_counter,
        "Dy": user.Dy,
        "actual_pressure": user.actual_pressure,
        "consumption_hour": user.consumption_hour,
        "pressure_drop": user.pressure_drop,
        "gas_density": user.gas_density,
        "DP": DP,
        "fg_actual": round(user.pressure_drop * 0.1), # Для диаграммы "Факт" -> style
        "fg": round(DP * 0.1),                   # Для диаграммы "Расчет" -> style
        "differential_value": differential_value,
        })



