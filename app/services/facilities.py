import math

FACILITIES = [
    {
        "id": "rsud_dr_soetomo",
        "name": "RSUD Dr. Soetomo",
        "type": "hospital",
        "address": "Jl. Mayjend Prof. Dr. Moestopo No.6-8, Surabaya",
        "lat": -7.2657,
        "lng": 112.7527,
        "phone": "+6231-5501078",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru lt. 2",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "DOTS TB"]
    },
    {
        "id": "rsal_dr_ramelan",
        "name": "RSAL Dr. Ramelan",
        "type": "hospital",
        "address": "Jl. Gadung No.1, Jagir, Wonokromo, Surabaya",
        "lat": -7.301,
        "lng": 112.737,
        "phone": "+6231-8438265",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "DOTS TB"]
    },
    {
        "id": "rs_william_booth",
        "name": "RS William Booth",
        "type": "hospital",
        "address": "Jl. Diponegoro No.34, Darmo, Wonokromo, Surabaya",
        "lat": -7.2823,
        "lng": 112.7319,
        "phone": "+6231-5678917",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "Poli Umum"]
    },
    {
        "id": "rs_siloam_surabaya",
        "name": "RS Siloam Surabaya",
        "type": "hospital",
        "address": "Jl. Raya Gubeng No.70, Surabaya",
        "lat": -7.2659,
        "lng": 112.752,
        "phone": "+6231-5025811",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "Poli Spesialis"]
    },
    {
        "id": "rs_premier_surabaya",
        "name": "RS Premier Surabaya",
        "type": "hospital",
        "address": "Jl. Nginden Intan Barat Blok B No.1, Surabaya",
        "lat": -7.3028,
        "lng": 112.7706,
        "phone": "+6231-5993211",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "Poli Spesialis"]
    },
    {
        "id": "rs_husada_utama",
        "name": "RS Husada Utama",
        "type": "hospital",
        "address": "Jl. Prof. Dr. Moestopo No.31-35, Surabaya",
        "lat": -7.2701,
        "lng": 112.753,
        "phone": "+6231-5013000",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "DOTS TB"]
    },
    {
        "id": "rsud_bhakti_dharma_husada",
        "name": "RSUD Bhakti Dharma Husada",
        "type": "hospital",
        "address": "Jl. Raya Kendung No.115-117, Surabaya",
        "lat": -7.2372,
        "lng": 112.6655,
        "phone": "+6231-7413839",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "DOTS TB"]
    },
    {
        "id": "rs_royal_surabaya",
        "name": "RS Royal Surabaya",
        "type": "hospital",
        "address": "Jl. Raya Gubeng No.19, Surabaya",
        "lat": -7.268,
        "lng": 112.751,
        "phone": "+6231-5033111",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi"]
    },
    {
        "id": "rs_adi_husada_undaan_wetan",
        "name": "RS Adi Husada Undaan Wetan",
        "type": "hospital",
        "address": "Jl. Undaan Wetan No.40-44, Surabaya",
        "lat": -7.2528,
        "lng": 112.7437,
        "phone": "+6231-5321256",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru lt.1",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "DOTS TB"]
    },
    {
        "id": "rs_mitra_keluarga_kenjeran",
        "name": "RS Mitra Keluarga Kenjeran",
        "type": "hospital",
        "address": "Jl. Kenjeran No.506, Surabaya",
        "lat": -7.2283,
        "lng": 112.7793,
        "phone": "+6231-3816161",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "Poli Spesialis"]
    },
    {
        "id": "rs_national_hospital",
        "name": "National Hospital Surabaya",
        "type": "hospital",
        "address": "Jl. Wijaya Kusuma No.11, Surabaya",
        "lat": -7.2846,
        "lng": 112.6537,
        "phone": "+6231-5755555",
        "operationalHours": "24 jam",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["IGD 24 Jam", "Rawat Inap", "Laboratorium", "Radiologi", "Poli Spesialis"]
    },
    {
        "id": "rsud_dr_moh_soewandhie",
        "name": "RSUD Dr. Moh. Soewandhie",
        "type": "hospital",
        "address": "Jl. Tambakrejo No.45-47, Surabaya",
        "lat": -7.2379,
        "lng": 112.7529,
        "phone": "+6231-3764555",
        "operationalHours": "24 jam",
        "isDotsCertified": True,
        "tbcUnit": "Poli Paru",
        "services": ["Poli Paru", "IGD 24 Jam", "Rawat Inap", "Laboratorium", "DOTS TB"]
    },
    {
        "id": "puskesmas_perak_timur",
        "name": "Puskesmas Perak Timur",
        "type": "clinic",
        "address": "Jl. Perak Timur No.468, Surabaya",
        "lat": -7.215,
        "lng": 112.7297,
        "phone": "+6231-3291543",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "Imunisasi", "DOTS TB"]
    },
    {
        "id": "puskesmas_tanah_kali_kedinding",
        "name": "Puskesmas Tanah Kali Kedinding",
        "type": "clinic",
        "address": "Jl. Tanah Kali Kedinding No.221, Surabaya",
        "lat": -7.2199,
        "lng": 112.7553,
        "phone": "+6231-3817426",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB", "Laboratorium Dasar"]
    },
    {
        "id": "puskesmas_simolawang",
        "name": "Puskesmas Simolawang",
        "type": "clinic",
        "address": "Jl. Simolawang No.33, Surabaya",
        "lat": -7.2402,
        "lng": 112.7414,
        "phone": "+6231-3714445",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    },
    {
        "id": "puskesmas_wonokromo",
        "name": "Puskesmas Wonokromo",
        "type": "clinic",
        "address": "Jl. Wonokromo No.35, Surabaya",
        "lat": -7.3035,
        "lng": 112.7258,
        "phone": "+6231-8490118",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "Imunisasi", "DOTS TB"]
    },
    {
        "id": "puskesmas_putat_jaya",
        "name": "Puskesmas Putat Jaya",
        "type": "clinic",
        "address": "Jl. Putat Jaya Barat I/I, Surabaya",
        "lat": -7.295,
        "lng": 112.7081,
        "phone": "+6231-5615590",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    },
    {
        "id": "puskesmas_sidotopo",
        "name": "Puskesmas Sidotopo",
        "type": "clinic",
        "address": "Jl. Sidotopo Wetan Baru No.7, Surabaya",
        "lat": -7.2347,
        "lng": 112.7607,
        "phone": "+6231-3763782",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    },
    {
        "id": "puskesmas_mulyorejo",
        "name": "Puskesmas Mulyorejo",
        "type": "clinic",
        "address": "Jl. Mulyorejo No.42, Surabaya",
        "lat": -7.2717,
        "lng": 112.8028,
        "phone": "+6231-5966774",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["Poli Umum", "KIA", "Imunisasi", "Gigi"]
    },
    {
        "id": "puskesmas_tambaksari",
        "name": "Puskesmas Tambaksari",
        "type": "clinic",
        "address": "Jl. Rangkah VI No.27, Surabaya",
        "lat": -7.2546,
        "lng": 112.7609,
        "phone": "+6231-5942100",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB", "Laboratorium Dasar"]
    },
    {
        "id": "klinik_rafa_medika",
        "name": "Klinik Rafa Medika",
        "type": "clinic",
        "address": "Jl. Rungkut Asri Tengah No.12, Surabaya",
        "lat": -7.3154,
        "lng": 112.7821,
        "phone": "+6231-8700900",
        "operationalHours": "08:00 - 21:00",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["Poli Umum", "Poli Gigi", "Laboratorium Dasar"]
    },
    {
        "id": "klinik_pratama_delta_husada",
        "name": "Klinik Pratama Delta Husada",
        "type": "clinic",
        "address": "Jl. Ketintang Baru Selatan I No.1, Surabaya",
        "lat": -7.3108,
        "lng": 112.7262,
        "phone": None,
        "operationalHours": "08:00 - 20:00",
        "isDotsCertified": False,
        "tbcUnit": None,
        "services": ["Poli Umum", "KIA", "Imunisasi"]
    },
    {
        "id": "puskesmas_gayungan",
        "name": "Puskesmas Gayungan",
        "type": "clinic",
        "address": "Jl. Gayungan PTT No.2, Surabaya",
        "lat": -7.332,
        "lng": 112.729,
        "phone": "+6231-8291314",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    },
    {
        "id": "puskesmas_dukuh_kupang",
        "name": "Puskesmas Dukuh Kupang",
        "type": "clinic",
        "address": "Jl. Dukuh Kupang XXV No.1, Surabaya",
        "lat": -7.2762,
        "lng": 112.7082,
        "phone": "+6231-5616232",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    },
    {
        "id": "puskesmas_sawahan",
        "name": "Puskesmas Sawahan",
        "type": "clinic",
        "address": "Jl. Kupang Panjaan I No.2, Surabaya",
        "lat": -7.268,
        "lng": 112.7193,
        "phone": "+6231-5672220",
        "operationalHours": "07:00 - 14:00",
        "isDotsCertified": True,
        "tbcUnit": "Poli TB",
        "services": ["Poli Umum", "Poli TB", "KIA", "DOTS TB"]
    }
]

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * (math.sin(d_lon / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def find_nearest_facility(user_lat, user_lng, facility_type=None, dots_only=False):
    nearest = None
    min_dist = float('inf')
    
    for f in FACILITIES:
        if facility_type and f["type"] != facility_type:
            continue
        if dots_only and not f["isDotsCertified"]:
            continue
            
        dist = haversine_km(user_lat, user_lng, f["lat"], f["lng"])
        if dist < min_dist:
            min_dist = dist
            nearest = f
            
    return nearest, min_dist
