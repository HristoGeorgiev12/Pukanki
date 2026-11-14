import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Comprehensive common English / foreign names dictionary to Bulgarian
NAME_MAP = {
    # First names
    "aaron": "Арън", "abigail": "Абигейл", "adam": "Адам", "alan": "Алън", "albert": "Албърт",
    "alec": "Алек", "alex": "Алекс", "alexander": "Александър", "alfred": "Алфред", "alice": "Алис",
    "alicia": "Алисия", "alison": "Алисън", "allan": "Алън", "allen": "Алън", "amanda": "Аманда",
    "amber": "Амбър", "amy": "Ейми", "andrew": "Андрю", "andy": "Анди", "angela": "Анджела",
    "angelina": "Анджелина", "anna": "Ана", "anne": "Ан", "anthony": "Антъни", "antonio": "Антонио",
    "arnold": "Арнолд", "arthur": "Артър", "ashley": "Ашли", "audrey": "Одри", "austin": "Остин",
    "barry": "Бари", "ben": "Бен", "benjamin": "Бенджамин", "bernard": "Бърнард", "beth": "Бет",
    "bill": "Бил", "billy": "Били", "blake": "Блейк", "blair": "Блеър", "bob": "Боб", "bobby": "Боби",
    "brad": "Брад", "bradley": "Брадли", "brandon": "Брандън", "brenda": "Бренда", "brent": "Брент",
    "brett": "Брет", "brian": "Брайън", "bridget": "Бриджит", "brittany": "Британи", "brooke": "Брук",
    "bruce": "Брус", "bryan": "Брайън", "caitlin": "Кейтлин", "cameron": "Камерън", "candice": "Кандис",
    "carl": "Карл", "carla": "Карла", "carlos": "Карлос", "carol": "Карол", "caroline": "Каролин",
    "casey": "Кейси", "catherine": "Катрин", "cate": "Кейт", "chad": "Чад", "charles": "Чарлз",
    "charlie": "Чарли", "charlotte": "Шарлот", "chelsea": "Челси", "chloe": "Клои", "chris": "Крис",
    "christian": "Крисчън", "christina": "Кристина", "christine": "Кристин", "christopher": "Кристофър",
    "cillian": "Килиън", "claire": "Клеър", "clark": "Кларк", "clint": "Клинт", "clive": "Клайв",
    "cody": "Коди", "colin": "Колин", "connie": "Кони", "connor": "Конър", "corey": "Кори",
    "courtney": "Кортни", "craig": "Крейг", "curtis": "Къртис", "cynthia": "Синтия",
    "dale": "Дейл", "damon": "Деймън", "dan": "Дан", "dana": "Дана", "daniel": "Даниел",
    "danielle": "Даниел", "danny": "Дани", "daphne": "Дафни", "daryl": "Дарил", "dave": "Дейв",
    "david": "Дейвид", "dawn": "Дон", "dean": "Дийн", "debbie": "Деби", "deborah": "Дебора",
    "denise": "Денис", "dennis": "Денис", "denzel": "Дензъл", "derek": "Дерек", "derrick": "Дерик",
    "diana": "Даяна", "diane": "Даян", "dick": "Дик", "diego": "Диего", "dillon": "Дилън",
    "dina": "Дина", "don": "Дон", "donald": "Доналд", "donna": "Дона", "dorothy": "Дороти",
    "doug": "Дъг", "douglas": "Дъглас", "drew": "Дрю", "dustin": "Дъстин", "dwayne": "Дуейн",
    "dylan": "Дилън", "ed": "Ед", "eddie": "Еди", "edgar": "Едгар", "edmund": "Едмънд",
    "edward": "Едуард", "edwin": "Едуин", "eileen": "Айлийн", "elaine": "Илейн", "elijah": "Илайджа",
    "elizabeth": "Елизабет", "ellen": "Елън", "elliot": "Елиът", "elliott": "Елиът", "elton": "Елтън",
    "elvis": "Елвис", "emily": "Емили", "emma": "Ема", "eric": "Ерик", "erik": "Ерик",
    "erin": "Ерин", "ernest": "Ърнест", "ethan": "Итън", "eugene": "Юджийн", "eva": "Ева",
    "evan": "Евън", "evelyn": "Евелин", "ewan": "Юън", "faye": "Фей", "felicity": "Фелисити",
    "fiona": "Фиона", "florence": "Флорънс", "ford": "Форд", "forrest": "Форест", "frances": "Франсис",
    "francis": "Франсис", "frank": "Франк", "frankie": "Франки", "fred": "Фред", "freddie": "Фреди",
    "frederick": "Фредерик", "gabriel": "Гейбриъл", "garrett": "Гарет", "gary": "Гари", "gavin": "Гавин",
    "gene": "Джийн", "geoffrey": "Джефри", "george": "Джордж", "gerald": "Джералд", "gerard": "Джерард",
    "gillian": "Джилиан", "gina": "Джина", "glen": "Глен", "glenn": "Глен", "gloria": "Глория",
    "gordon": "Гордън", "grace": "Грейс", "graham": "Греъм", "grant": "Грант", "greg": "Грег",
    "gregory": "Грегъри", "guy": "Гай", "gwen": "Гуен", "gwyneth": "Гуинет", "hailey": "Хейли",
    "hal": "Хал", "hank": "Ханк", "hannah": "Хана", "harold": "Харолд", "harriet": "Хариет",
    "harris": "Харис", "harrison": "Харисън", "harry": "Хари", "harvey": "Харви", "hayden": "Хейдън",
    "heath": "Хийт", "heather": "Хедър", "helen": "Хелън", "helena": "Хелена", "henry": "Хенри",
    "hilary": "Хилъри", "hillary": "Хилъри", "holly": "Холи", "howard": "Хауърд", "hugh": "Хю",
    "hugo": "Хюго", "ian": "Иън", "idris": "Идрис", "irene": "Айрийн", "isaac": "Айзък",
    "isabel": "Изабел", "isabella": "Изабела", "jack": "Джак", "jackie": "Джаки", "jackson": "Джаксън",
    "jacob": "Джейкъб", "jacqueline": "Жаклин", "jake": "Джейк", "james": "Джеймс", "jamie": "Джейми",
    "jan": "Джан", "jane": "Джейн", "janet": "Джанет", "janice": "Джанис", "jared": "Джаред",
    "jason": "Джейсън", "jay": "Джей", "jean": "Жан", "jeff": "Джеф", "jeffrey": "Джефри",
    "jenna": "Джена", "jennifer": "Дженифър", "jeremy": "Джеръми", "jerry": "Джери", "jesse": "Джеси",
    "jessica": "Джесика", "jim": "Джим", "jimmy": "Джими", "joan": "Джоан", "joaquin": "Хоакин",
    "jodie": "Джоди", "joe": "Джо", "joel": "Джоел", "john": "Джон", "johnny": "Джони",
    "jon": "Джон", "jonah": "Джона", "jonathan": "Джонатан", "jordan": "Джордан", "jose": "Хосе",
    "joseph": "Джоузеф", "josh": "Джош", "joshua": "Джошуа", "joyce": "Джойс", "jude": "Джуд",
    "judith": "Джудит", "judy": "Джуди", "julia": "Джулия", "julian": "Джулиан", "julie": "Джули",
    "justin": "Джъстин", "kareem": "Карим", "karen": "Карън", "karl": "Карл", "kate": "Кейт",
    "katherine": "Катрин", "kathleen": "Катлийн", "kathryn": "Катрин", "katie": "Кейти", "kay": "Кей",
    "keanu": "Киану", "keira": "Кийра", "keith": "Кийт", "kelly": "Кели", "kelsey": "Келси",
    "ken": "Кен", "kenneth": "Кенет", "kevin": "Кевин", "kim": "Ким", "kirsten": "Кирстен",
    "kristen": "Кристен", "kurt": "Кърт", "kyle": "Кайл", "lance": "Ланс", "larry": "Лари",
    "laura": "Лора", "lauren": "Лорън", "laurence": "Лорънс", "lawrence": "Лорънс", "leah": "Лия",
    "lee": "Лий", "leigh": "Лий", "leo": "Лео", "leon": "Леон", "leonard": "Ленард",
    "leonardo": "Леонардо", "leslie": "Лесли", "liam": "Лиъм", "lillian": "Лилиън", "lily": "Лили",
    "linda": "Линда", "lindsay": "Линдзи", "lisa": "Лиса", "liz": "Лиз", "lizzie": "Лизи",
    "lloyd": "Лойд", "logan": "Логан", "lois": "Лоис", "lori": "Лори", "louis": "Луис",
    "lucas": "Лукас", "lucille": "Лусил", "lucy": "Луси", "luke": "Люк", "lynn": "Лин",
    "maggie": "Маги", "malcolm": "Малкълм", "mandy": "Манди", "manuel": "Мануел", "marc": "Марк",
    "marcus": "Маркъс", "margaret": "Маргарет", "margo": "Марго", "maria": "Мария", "marilyn": "Мерилин",
    "marion": "Мериън", "mark": "Марк", "marlene": "Марлене", "martha": "Марта", "martin": "Мартин",
    "mary": "Мери", "mason": "Мейсън", "matthew": "Матю", "maurice": "Морис", "max": "Макс",
    "megan": "Меган", "mel": "Мел", "melanie": "Мелани", "melissa": "Мелиса", "meredith": "Мередит",
    "mia": "Миа", "michael": "Майкъл", "michelle": "Мишел", "mick": "Мик", "mickey": "Мики",
    "mike": "Майк", "miles": "Майлс", "milo": "Майло", "miranda": "Миранда", "mitchell": "Мичъл",
    "molly": "Моли", "monica": "Моника", "morgan": "Морган", "morris": "Морис", "nancy": "Нанси",
    "naomi": "Наоми", "natalie": "Натали", "nathan": "Нейтън", "neil": "Нийл", "nicholas": "Никълъс",
    "nick": "Ник", "nicolas": "Никълъс", "nicole": "Никол", "nina": "Нина", "noah": "Ноа",
    "nora": "Нора", "norman": "Норман", "oliver": "Оливър", "olivia": "Оливия", "omar": "Омар",
    "orlando": "Орландо", "oscar": "Оскар", "owen": "Оуен", "paige": "Пейдж", "pamela": "Памела",
    "pat": "Пат", "patricia": "Патриша", "patrick": "Патрик", "paul": "Пол", "paula": "Пола",
    "peggy": "Пеги", "penelope": "Пенелопе", "penny": "Пени", "perry": "Пери", "pete": "Пийт",
    "peter": "Питър", "phil": "Фил", "philip": "Филип", "phillip": "Филип", "phoebe": "Фийби",
    "pierce": "Пиърс", "quentin": "Куентин", "rachel": "Рейчъл", "ralph": "Ралф", "ramon": "Рамон",
    "randy": "Ранди", "ray": "Рей", "raymond": "Реймънд", "rebecca": "Ребека", "reed": "Рийд",
    "reese": "Рийз", "renee": "Рене", "rex": "Рекс", "rhonda": "Ронда", "richard": "Ричард",
    "rick": "Рик", "ricky": "Рики", "riley": "Райли", "rita": "Рита", "rob": "Роб",
    "robbie": "Роби", "robert": "Робърт", "roberta": "Роберта", "robin": "Робин", "rod": "Род",
    "rodney": "Родни", "roger": "Роджър", "roland": "Роланд", "ron": "Рон", "ronald": "Роналд",
    "ronnie": "Рони", "rory": "Рори", "rose": "Роуз", "rosie": "Роузи", "ross": "Рос",
    "roy": "Рой", "russell": "Ръсел", "ruth": "Рут", "ryan": "Райън", "sam": "Сам",
    "samantha": "Саманта", "samuel": "Самюъл", "sandra": "Сандра", "sara": "Сара", "sarah": "Сара",
    "scott": "Скот", "sean": "Шон", "sebastian": "Себастиан", "selena": "Селена", "seth": "Сет",
    "shane": "Шейн", "shannon": "Шанън", "sharon": "Шарън", "shaun": "Шон", "shawn": "Шон",
    "sheila": "Шейла", "shelby": "Шелби", "sherry": "Шери", "shirley": "Шърли", "sydney": "Сидни",
    "sidney": "Сидни", "sienna": "Сиена", "simon": "Саймън", "sofia": "София", "sophia": "София",
    "sophie": "Софи", "spencer": "Спенсър", "stacy": "Стейси", "stan": "Стан", "stanley": "Станли",
    "stella": "Стела", "stephanie": "Стефани", "stephen": "Стивън", "steve": "Стийв", "steven": "Стивън",
    "stewart": "Стюарт", "susan": "Сюзън", "suzanne": "Сюзан", "sylvia": "Силвия", "tara": "Тара",
    "taylor": "Тейлър", "ted": "Тед", "terence": "Терънс", "teresa": "Тереза", "terry": "Тери",
    "theodore": "Теодор", "thomas": "Томас", "tim": "Тим", "timothy": "Тимъти", "tina": "Тина",
    "toby": "Тоби", "todd": "Тод", "tom": "Том", "tommy": "Томи", "tony": "Тони",
    "tracey": "Трейси", "tracy": "Трейси", "travis": "Травис", "trevor": "Тревър", "tyler": "Тайлър",
    "val": "Вал", "valerie": "Валери", "vanessa": "Ванеса", "veronica": "Вероника", "victor": "Виктор",
    "victoria": "Виктория", "vince": "Винс", "vincent": "Винсънт", "viola": "Вайола", "virginia": "Вирджиния",
    "vivian": "Вивиан", "vivica": "Вивика", "walter": "Уолтър", "warren": "Уорън", "wayne": "Уейн",
    "wendy": "Уенди", "wesley": "Уесли", "will": "Уил", "william": "Уилям", "willie": "Уили",
    "woody": "Уди", "zach": "Зак", "zachary": "Закари", "zoe": "Зоуи",

    # Common surnames
    "adams": "Адамс", "alexander": "Александър", "allen": "Алън", "anderson": "Андерсън",
    "angarano": "Ангарано", "armstrong": "Армстронг", "arnold": "Арнолд", "atkinson": "Аткинсън",
    "bailey": "Бейли", "baker": "Бейкър", "baldwin": "Болдуин", "bale": "Бейл", "banks": "Банкс",
    "barker": "Баркър", "barnes": "Барнс", "barrett": "Барет", "barry": "Бари", "barton": "Бартън",
    "bates": "Бейтс", "beck": "Бек", "bell": "Бел", "bennett": "Бенет", "berry": "Бери",
    "bishop": "Бишъп", "black": "Блек", "blake": "Блейк", "blunt": "Блънт", "bond": "Бонд",
    "boone": "Бун", "booth": "Бут", "bowen": "Боуен", "bowman": "Боуман", "boyd": "Бойд",
    "boyle": "Бойл", "bradley": "Брадли", "brady": "Брейди", "bridges": "Бриджис", "broberg": "Броберг",
    "brody": "Броди", "brooks": "Брукс", "brown": "Браун", "bullock": "Бълок", "burns": "Бърнс",
    "burton": "Бъртън", "butler": "Бътлър", "byrne": "Бърн", "cage": "Кейдж", "cameron": "Камерън",
    "campbell": "Кембъл", "carey": "Кери", "carlson": "Карлсън", "carney": "Карни", "carpenter": "Карпентър",
    "carr": "Кар", "carroll": "Карол", "carter": "Картър", "casey": "Кейси", "chambers": "Чеймбърс",
    "chan": "Чан", "chandler": "Чандлър", "chapman": "Чапман", "chase": "Чейс", "chuchran": "Чакран",
    "clark": "Кларк", "clarke": "Кларк", "cochran": "Кокран", "cohen": "Коен", "cole": "Коул",
    "coleman": "Колман", "collins": "Колинс", "connery": "Конъри", "conway": "Конуей", "cook": "Кук",
    "cooper": "Купър", "coppola": "Копола", "cox": "Кокс", "craig": "Крейг", "crawford": "Крофорд",
    "cross": "Крос", "cruise": "Круз", "cummings": "Къмингс", "cunningham": "Кънингам", "curtis": "Къртис",
    "daniels": "Даниелс", "davidson": "Дейвидсън", "davies": "Дейвис", "davis": "Дейвис", "dawson": "Доусън",
    "day": "Дей", "dean": "Дийн", "depp": "Деп", "diaz": "Диас", "dickson": "Диксън", "dixon": "Диксън",
    "douglas": "Дъглас", "doyle": "Дойл", "drake": "Дрейк", "dudley": "Дъдли", "duncan": "Дънкан",
    "dunn": "Дън", "eastwood": "Истууд", "eaton": "Ийтън", "edwards": "Едуардс", "elliott": "Елиът",
    "ellis": "Елис", "evans": "Еванс", "farrell": "Фарел", "faulkner": "Фокнър", "felt": "Фелт",
    "ferguson": "Фъргюсън", "fiennes": "Файнс", "fincher": "Финчър", "fischer": "Фишер", "fisher": "Фишър",
    "fitzgerald": "Фицджералд", "fleming": "Флеминг", "fletcher": "Флетчър", "flores": "Флорес",
    "flynn": "Флин", "foley": "Фоли", "ford": "Форд", "forster": "Форстър", "foster": "Фостър",
    "fowler": "Фаулър", "fox": "Фокс", "franklin": "Франклин", "fraser": "Фрейзър", "freeman": "Фрийман",
    "frost": "Фрост", "fry": "Фрай", "fuller": "Фулър", "gallagher": "Галахър", "gardner": "Гарднър",
    "garrett": "Гарет", "gates": "Гейтс", "gibson": "Гибсън", "gilbert": "Гилбърт", "giles": "Джайлс",
    "gill": "Гил", "glover": "Глоувър", "godfrey": "Годфри", "goldberg": "Голдбърг", "goldblum": "Голдблум",
    "goodman": "Гудман", "goodwin": "Гудуин", "gordon": "Гордън", "gosling": "Гослинг", "gould": "Гулд",
    "graham": "Греъм", "grant": "Грант", "graves": "Грейвс", "gray": "Грей", "green": "Грийн",
    "greene": "Грийн", "gregory": "Грегъри", "griffin": "Грифин", "griffith": "Грифит", "gunn": "Гън",
    "haines": "Хейнс", "hale": "Хейл", "haley": "Хейли", "hall": "Хол", "hamilton": "Хамилтън",
    "hammond": "Хамънд", "hancock": "Ханкок", "hanks": "Ханкс", "hansen": "Хансен", "hanson": "Хансън",
    "hardy": "Харди", "harper": "Харпър", "harris": "Харис", "harrison": "Харисън", "hart": "Харт",
    "hartman": "Хартман", "harvey": "Харви", "hathaway": "Хатауей", "hawke": "Хоук", "hawkins": "Хокинс",
    "hayes": "Хейс", "haynes": "Хейнс", "hayward": "Хейуърд", "head": "Хед", "heath": "Хийт",
    "hemsworth": "Хемсуърт", "henderson": "Хендерсън", "henry": "Хенри", "herman": "Хърман",
    "hickner": "Хикнър", "hicks": "Хикс", "higgins": "Хигинс", "hill": "Хил", "hitchcock": "Хичкок",
    "hobbs": "Хобс", "hodge": "Ходж", "hodges": "Ходжис", "hoffman": "Хофман", "hogan": "Хоган",
    "holland": "Холанд", "holloway": "Холоуей", "holmes": "Холмс", "holt": "Холт", "hood": "Худ",
    "hopkins": "Хопкинс", "horton": "Хортън", "house": "Хаус", "houston": "Хюстън", "howard": "Хауърд",
    "howe": "Хау", "howell": "Хауъл", "hubbard": "Хъбард", "hudson": "Хъдсън", "hughes": "Хюз",
    "hunt": "Хънт", "hunter": "Хънтър", "hurley": "Хърли", "hutchinson": "Хътчинсън", "ingram": "Ингръм",
    "irwin": "Ъруин", "jackson": "Джаксън", "jacobs": "Джейкъбс", "james": "Джеймс", "jarvis": "Джарвис",
    "jenkins": "Дженкинс", "jennings": "Дженингс", "jensen": "Дженсен", "johnson": "Джонсън",
    "johnston": "Джонстън", "jones": "Джоунс", "jordan": "Джордан", "kane": "Кейн", "kaufman": "Кауфман",
    "kearney": "Карни", "keaton": "Кийтън", "keith": "Кийт", "kellar": "Келър", "keller": "Келър",
    "kelley": "Кели", "kelly": "Кели", "kemp": "Кемп", "kendall": "Кендъл", "kennedy": "Кенеди",
    "kent": "Кент", "kerr": "Кър", "kidd": "Кид", "kidman": "Кидман", "kiernan": "Киърнан",
    "kilmer": "Килмър", "king": "Кинг", "kirby": "Кърби", "kirk": "Кърк", "knight": "Найт",
    "knox": "Нокс", "kramer": "Креймър", "kubrick": "Кубрик", "kudrow": "Кудроу", "lambert": "Ламбърт",
    "lancaster": "Ланкастър", "lane": "Лейн", "lang": "Ланг", "larson": "Ларсън", "law": "Лоу",
    "lawrence": "Лорънс", "lawson": "Лосън", "leach": "Лийч", "leblanc": "Лебланк", "lee": "Лий",
    "lewis": "Луис", "lincoln": "Линкълн", "lindsey": "Линдзи", "little": "Литъл", "lloyd": "Лойд",
    "locke": "Лок", "logan": "Логан", "long": "Лонг", "love": "Лъв", "lowe": "Лоу",
    "lucas": "Лукас", "lynch": "Линч", "lyon": "Лайън", "lyons": "Лайънс", "macdonald": "Макдоналд",
    "mack": "Мак", "macy": "Мейси", "madden": "Мадън", "madison": "Мадисън", "maguire": "Магуайър",
    "manning": "Манинг", "mansfield": "Мансфийлд", "marks": "Маркс", "marsh": "Марш", "marshall": "Маршал",
    "martin": "Мартин", "mason": "Мейсън", "massey": "Маси", "matthews": "Матюс", "maxwell": "Максуел",
    "may": "Мей", "mayer": "Майер", "maynard": "Мейнард", "mccarthy": "Маккарти", "mccormick": "Маккормик",
    "mccoy": "Маккой", "mcdonald": "Макдоналд", "mcgee": "Макгий", "mcgregor": "Макгрегър",
    "mckay": "Маккей", "mckenzie": "Маккензи", "mckinney": "Макини", "mclaughlin": "Маклафлин",
    "mclean": "Маклийн", "mcmahon": "Макмеън", "mcpherson": "Макферсън", "mercer": "Мърсър",
    "merrill": "Мерил", "meyer": "Майер", "meyers": "Майърс", "middleton": "Мидълтън", "miles": "Майлс",
    "miller": "Милър", "mills": "Милс", "milner": "Милнър", "milton": "Милтън", "mirren": "Мирън",
    "mitchell": "Мичъл", "monroe": "Монро", "montgomery": "Монтгомъри", "moody": "Муди", "moore": "Мур",
    "morgan": "Морган", "morley": "Морли", "morris": "Морис", "morrison": "Морисън", "morrow": "Мороу",
    "morse": "Морс", "morton": "Мортън", "moss": "Мос", "murphy": "Мърфи", "murray": "Мъри",
    "myers": "Майърс", "nash": "Наш", "neal": "Нийл", "nelson": "Нелсън", "newman": "Нюман",
    "newton": "Нютън", "nichols": "Никълс", "nicholson": "Никълсън", "nixon": "Никсън", "noble": "Нобъл",
    "nolan": "Нолан", "norman": "Норман", "norris": "Норис", "norton": "Нортън", "o'brien": "О'Брайън",
    "o'connor": "О'Конър", "o'neill": "О'Нийл", "oliver": "Оливър", "olsen": "Олсен", "olson": "Олсън",
    "owen": "Оуен", "owens": "Оуенс", "pace": "Пейс", "page": "Пейдж", "palmer": "Палмър",
    "parker": "Паркър", "parkinson": "Паркинсън", "parks": "Паркс", "parrish": "Париш", "parson": "Парсън",
    "parsons": "Парсънс", "patch": "Пач", "patel": "Пател", "paterson": "Патерсън", "patrick": "Патрик",
    "patterson": "Патерсън", "patton": "Патън", "paul": "Пол", "paxton": "Пакстън", "payne": "Пейн",
    "pearson": "Пиърсън", "peck": "Пек", "perkins": "Пъркинс", "perry": "Пери", "peters": "Питърс",
    "peterson": "Питърсън", "pfeiffer": "Пфайфър", "phelps": "Фелпс", "phillips": "Филипс", "pierce": "Пиърс",
    "pierson": "Пиърсън", "pitt": "Пит", "platt": "Плат", "poole": "Пул", "pope": "Поуп",
    "porter": "Портър", "potter": "Потър", "powell": "Пауъл", "power": "Пауър", "powers": "Пауърс",
    "pratt": "Прат", "prescott": "Прескот", "preston": "Престън", "price": "Прайс", "prince": "Принс",
    "quinn": "Куин", "ramsay": "Рамзи", "ramsey": "Рамзи", "randall": "Рандъл", "ray": "Рей",
    "reed": "Рийд", "rees": "Рийз", "reese": "Рийз", "reeve": "Рийв", "reeves": "Рийвс",
    "reid": "Рийд", "reilly": "Райли", "reynolds": "Рейнолдс", "rhodes": "Роудс", "rice": "Райс",
    "rich": "Рич", "richards": "Ричардс", "richardson": "Ричардсън", "richmond": "Ричмънд", "riddle": "Ридъл",
    "riggs": "Ригс", "riley": "Райли", "ritchie": "Ричи", "rivers": "Ривърс", "robbins": "Робинс",
    "roberts": "Робъртс", "robertson": "Робъртсън", "robinson": "Робинсън", "rodgers": "Роджърс", "rogers": "Роджърс",
    "ross": "Рос", "roth": "Рот", "rowe": "Роу", "rowland": "Роуланд", "rudd": "Ръд",
    "rush": "Ръш", "russell": "Ръсел", "ryan": "Райън", "ryder": "Райдър", "sanders": "Сандърс",
    "sawyer": "Сойър", "schmidt": "Шмид", "schneider": "Шнайдер", "schwarzenegger": "Шварценегер",
    "schwimmer": "Шуимър", "scorsese": "Скорсезе", "scott": "Скот", "seymour": "Сеймур", "sharp": "Шарп",
    "sharpe": "Шарп", "shaw": "Шоу", "shea": "Шей", "sheeran": "Шийрън", "shelton": "Шелтън",
    "shepard": "Шепърд", "shepherd": "Шепърд", "sherman": "Шърман", "shields": "Шийлдс", "short": "Шорт",
    "simon": "Саймън", "simons": "Саймънс", "simpson": "Симпсън", "sinclair": "Синклер", "slater": "Слейтър",
    "smith": "Смит", "snyder": "Снайдър", "spencer": "Спенсър", "spielberg": "Спилбърг", "stallone": "Сталоун",
    "stanton": "Стантън", "stark": "Старк", "statham": "Стейтъм", "steele": "Стийл", "stephens": "Стивънс",
    "stephenson": "Стивънсън", "stevens": "Стивънс", "stevenson": "Стивънсън", "stewart": "Стюарт",
    "stone": "Стоун", "streep": "Стрийп", "strickland": "Стрикланд", "strong": "Стронг", "stuart": "Стюарт",
    "sullivan": "Съливан", "summers": "Съмърс", "sutherland": "Съдърланд", "sutton": "Сътън",
    "swanson": "Суонсън", "swift": "Суифт", "tanner": "Танър", "tarantino": "Тарантино", "taylor": "Тейлър",
    "temple": "Темпъл", "terry": "Тери", "thomas": "Томас", "thompson": "Томпсън", "thomson": "Томсън",
    "thornton": "Торнтън", "thurman": "Търман", "todd": "Тод", "townsend": "Таунсенд", "travis": "Травис",
    "treu": "Трю", "tucker": "Тъкър", "turner": "Търнър", "tyler": "Тайлър", "underwood": "Ъндърууд",
    "vance": "Ванс", "vaughn": "Вон", "villeneuve": "Вилньов", "wade": "Уейд", "wagner": "Вагнер",
    "walker": "Уокър", "wall": "Уол", "wallace": "Уолъс", "waller": "Уолър", "walsh": "Уолш",
    "walter": "Уолтър", "walters": "Уолтърс", "walton": "Уолтън", "ward": "Уорд", "ware": "Уеър",
    "warner": "Уорнър", "warren": "Уорън", "washington": "Уошингтън", "waters": "Уотърс", "watkins": "Уоткинс",
    "watson": "Уотсън", "watts": "Уотс", "weaver": "Уивър", "webb": "Уеб", "webster": "Уебстър",
    "wells": "Уелс", "west": "Уест", "wheeler": "Уилър", "whitaker": "Уитакер", "white": "Уайт",
    "whitehead": "Уайтхед", "whitney": "Уитни", "wilcox": "Уилкокс", "wilde": "Уайлд", "wilder": "Уайлдър",
    "wilkerson": "Уилкърсън", "wilkins": "Уилкинс", "wilkinson": "Уилкинсън", "williams": "Уилямс",
    "williamson": "Уилямсън", "willis": "Уилис", "wilson": "Уилсън", "winter": "Уинтър", "winters": "Уинтърс",
    "wise": "Уайз", "wolfe": "Улф", "wood": "Ууд", "woodard": "Уудард", "woods": "Уудс",
    "woodward": "Удуърд", "wright": "Райт", "wyatt": "Уайът", "yates": "Йейтс", "york": "Йорк",
    "young": "Йънг", "zimmerman": "Цимерман"
}


# Phonetic letter transliteration rules for any unmapped words
DIGRAPHS = [
    ("tch", "ч"), ("sch", "ш"), ("ght", "йт"), ("tion", "шън"), ("sion", "жън"),
    ("ch", "ч"), ("sh", "ш"), ("th", "т"), ("ph", "ф"), ("wh", "у"), ("ck", "к"),
    ("qu", "ку"), ("wr", "р"), ("kn", "н"), ("ee", "и"), ("ea", "и"), ("oo", "у"),
    ("ou", "у"), ("ow", "оу"), ("ai", "ей"), ("ay", "ей"), ("ei", "ей"), ("ey", "и"),
    ("ie", "и"), ("oa", "о"), ("au", "о"), ("aw", "о")
]

CHAR_MAP = {
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "х", "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "w": "у", "x": "кс", "y": "и", "z": "з"
}


def transliterate_word(word: str) -> str:
    clean = word.strip()
    if not clean:
        return ""
    if re.search(r"[\u0400-\u04FF]", clean):
        return clean

    low = clean.lower()
    if low in NAME_MAP:
        res = NAME_MAP[low]
        return res.capitalize() if clean[0].isupper() else res

    # Phonetic digraphs
    out = low
    for pattern, rep in DIGRAPHS:
        out = out.replace(pattern, rep)

    # Single letters
    chars = []
    for ch in out:
        chars.append(CHAR_MAP.get(ch, ch))

    res = "".join(chars)
    return res.capitalize() if clean[0].isupper() else res


def cyrillicize_name(full_name: str) -> str:
    if not full_name or not isinstance(full_name, str):
        return full_name
    if re.search(r"[\u0400-\u04FF]", full_name):
        # Already has Cyrillic; only transliterate Latin parts if mixed
        parts = re.split(r"(\s+|[.,\-/])", full_name)
        res_parts = []
        for p in parts:
            if re.match(r"^[A-Za-z]+$", p):
                res_parts.append(transliterate_word(p))
            else:
                res_parts.append(p)
        return "".join(res_parts)

    parts = re.split(r"(\s+|[.,\-/])", full_name)
    res_parts = []
    for p in parts:
        if re.match(r"^[A-Za-z]+$", p):
            res_parts.append(transliterate_word(p))
        else:
            res_parts.append(p)
    return "".join(res_parts)


def update_catalog(file_path: str, js_path: str, var_name: str):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    changed = 0
    for item in items:
        actors = item.get("actors")
        if isinstance(actors, list) and actors:
            new_actors = [cyrillicize_name(a) for a in actors]
            if new_actors != actors:
                item["actors"] = new_actors
                changed += 1

        directors = item.get("directors")
        if isinstance(directors, list) and directors:
            new_directors = [cyrillicize_name(d) for d in directors]
            if new_directors != directors:
                item["directors"] = new_directors
                changed += 1

    print(f"[{var_name}] Processed {len(items)} items, updated {changed} items with Cyrillic names.")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"window.{var_name} = {json.dumps(items, ensure_ascii=False)};\n")


def main():
    print("=== STARTING CYRILLIC NAME STANDARDIZATION ===")
    update_catalog(os.path.join(DATA_DIR, "movies.json"), os.path.join(DATA_DIR, "movies_data.js"), "MOVIES_DATA")
    update_catalog(os.path.join(DATA_DIR, "tv_shows.json"), os.path.join(DATA_DIR, "tv_shows_data.js"), "TV_SHOWS_DATA")
    update_catalog(os.path.join(DATA_DIR, "filmi2k_bg.json"), os.path.join(DATA_DIR, "filmi2k_bg_data.js"), "FILMI2K_BG_DATA")
    print("=== FINISHED CYRILLIC NAME STANDARDIZATION ===")


if __name__ == "__main__":
    main()

