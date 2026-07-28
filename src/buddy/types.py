from enum import Enum

class Species(str, Enum):
    CAT = "Kedi"
    ROBOT = "Robot"
    OWL = "Baykuş"
    DUCK = "Ördek"

SPRITES = {
    Species.CAT: [
        "   /\\_/\\   ",
        "  ( ◉   ◉)  ",
        "  (  ω  )   ",
        "  (\")_(\")  "
    ],
    Species.ROBOT: [
        "   .[||].   ",
        "  [ ◉  ◉ ]  ",
        "  [ ==== ]  ",
        "  `------´  "
    ],
    Species.OWL: [
        "   /\\  /\\   ",
        "  ((◉)(◉))  ",
        "  (  ><  )  ",
        "   ----´   "
    ],
    Species.DUCK: [
        "    __      ",
        "  <({E} )___ ",
        "   (  ._>   ",
        "    --´~    "
    ]
}

# Her karakterin (buddy) projeye veya sana kattığı özel bir yetenek:
ABILITIES = {
    Species.CAT: "Hata Avcısı: Karmaşık Traceback (Hata) loglarında asıl sorunu anında koklar.",
    Species.ROBOT: "Refactor Ustası: Yazdığın kodu inceler, performans ve Big-O optimizasyonu önerir.",
    Species.OWL: "Gece Kuşu: Gece geç saatlerde çalışırken gözlerini yormaman için terminal temalarını uyarır.",
    Species.DUCK: "Rubber Duck (Plastik Ördek): Kodda tıkandığında ona mantığını anlatırsın, seni dinleyip doğru yolu bulmanı sağlar."
}



