import psycopg2
from faker import Faker
import random

fake = Faker('tr_TR') # Türkçe veri üretimi için

# Veritabanı bağlantı bilgileri
DB_CONFIG = {
    "dbname": "sporthink_db", # Kendi DB adınızı yazın
    "user": "postgres",
    "password": "password",   # Kendi şifrenizi yazın
    "host": "localhost",
    "port": "5432"
}

def seed_step_1_and_2():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Veritabanına bağlanıldı. Seeding başlıyor...")

        # ---------------------------------------------------------
        # ADIM 1: ROLLER VE SİSTEM METRİĞİ (Statik Veriler)
        # ---------------------------------------------------------
        roller = ['admin', 'supervisor', 'personel', 'bt']
        rol_ids = {}
        for rol in roller:
            cur.execute("INSERT INTO roller (ad) VALUES (%s) ON CONFLICT (ad) DO NOTHING RETURNING id;", (rol,))
            res = cur.fetchone()
            if res:
                rol_ids[rol] = res[0]
            else:
                cur.execute("SELECT id FROM roller WHERE ad = %s;", (rol,))
                rol_ids[rol] = cur.fetchone()[0]
        print("✅ Roller eklendi.")

        # Sistem Metrikleri (Zorunlu ID=1 kuralı için)
        cur.execute("""
            INSERT INTO sistem_metrikleri (id, aktif_kanal_sayisi, trunk_limiti) 
            VALUES (1, 0, 100) ON CONFLICT (id) DO NOTHING;
        """)

        # ---------------------------------------------------------
        # ADIM 2: DEPARTMANLAR VE KUYRUKLAR
        # ---------------------------------------------------------
        departman_datalari = [
            ("Müşteri Hizmetleri", 1000, 1999, 1),
            ("Satış", 2000, 2999, 2),
            ("Teknik Destek", 3000, 3999, 3)
        ]
        
        departman_ids = {}
        for ad, d_bas, d_bit, ivr in departman_datalari:
            cur.execute("""
                INSERT INTO departmanlar (ad, dahili_baslangic, dahili_bitis, ivr_kodu)
                VALUES (%s, %s, %s, %s) ON CONFLICT (ad) DO NOTHING RETURNING id;
            """, (ad, d_bas, d_bit, ivr))
            res = cur.fetchone()
            dept_id = res[0] if res else None
            
            if not dept_id:
                cur.execute("SELECT id FROM departmanlar WHERE ad = %s;", (ad,))
                dept_id = cur.fetchone()[0]
            
            departman_ids[ad] = {"id": dept_id, "min": d_bas, "max": d_bit}
            
            # Her departmana 2 kuyruk ekle
            for i in range(1, 3):
                cur.execute("""
                    INSERT INTO kuyruklar (departman_id, kuyruk_no, ad) 
                    VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
                """, (dept_id, f"{ivr}0{i}", f"{ad} Kuyruk {i}"))
                
        print("✅ Departmanlar ve Kuyruklar oluşturuldu.")

        # ---------------------------------------------------------
        # ADIM 3: EKİPLER VE KULLANICILAR (Kurallara Uygun!)
        # ---------------------------------------------------------
        for dept_ad, dept_info in departman_ids.items():
            dept_id = dept_info["id"]
            
            # Ekipleri oluştur
            ekip_ad = f"{dept_ad} Alfa Ekibi"
            cur.execute("""
                INSERT INTO ekipler (departman_id, ad) VALUES (%s, %s) 
                ON CONFLICT DO NOTHING RETURNING id;
            """, (dept_id, ekip_ad))
            res = cur.fetchone()
            ekip_id = res[0] if res else None
            
            if not ekip_id:
                cur.execute("SELECT id FROM ekipler WHERE ad = %s AND departman_id = %s;", (ekip_ad, dept_id))
                ekip_id = cur.fetchone()[0]

            # Personel Oluştur (Dahili numaraları departman aralığında rastgele seçiyoruz)
            kullanilan_dahililer = set()
            for _ in range(5): # Her departmana 5 personel
                dahili = random.randint(dept_info["min"], dept_info["max"])
                while dahili in kullanilan_dahililer:
                    dahili = random.randint(dept_info["min"], dept_info["max"])
                kullanilan_dahililer.add(dahili)

                ad_soyad = fake.name()
                username = fake.user_name() + str(random.randint(10,99))
                
                # pg_crypto ile şifreleme db tarafında yapılıyor
                cur.execute("""
                    INSERT INTO kullanicilar 
                    (rol_id, departman_id, ekip_id, ad_soyad, kullanici_adi, sifre_hash, dahili_no)
                    VALUES (%s, %s, %s, %s, %s, crypt('123456', gen_salt('bf')), %s);
                """, (rol_ids['personel'], dept_id, ekip_id, ad_soyad, username, str(dahili)))

        print("✅ Ekipler ve Personeller (Kurallara uygun dahili no ile) oluşturuldu.")
        
        conn.commit()
        cur.close()
        conn.close()
        print("🎉 Aşama 1 ve 2 başarıyla tamamlandı!")

    except Exception as e:
        print(f"❌ Bir hata oluştu: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    seed_step_1_and_2()