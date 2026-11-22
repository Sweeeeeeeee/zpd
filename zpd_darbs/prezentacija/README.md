# Vieglu ģeometrijas risinājumu skeneris

[Astoņu slaidu prezentācija (PDF)](prezentacija.pdf) ir paredzēta septiņu minūšu mutiskam ziņojumam. Zemāk dotais runas plāns aizņem aptuveni 6 minūtes un 20 sekundes, ieskaitot pauzes pie zīmējumiem. Laiks ir mēģinājuma mērķis. Valsts posma stenda ziņojumam vadlīnijās aprakstīts atsevišķs formāts. [ZPD vadlīnijas, 18.–20. lpp.](../vadlinijas/vadlinijas_zpd_2026_2027.pdf)

## Runas piezīmes

### 1. Jautājums · 0:00–0:35

Kad skolēns iestrēgst ģeometrijas uzdevumā, viņam mēdz ieteikt novilkt vēl vienu taisni vai atzīmēt kādu viduspunktu. Kā varam pārbaudīt, vai tāds palīgpunkts tiešām vajadzīgs? Izveidoju skeneri, kas mēģina iegūt pierādījumu no dotajiem punktiem. Ja tas apstājas, var ieslēgt palīgpunktu meklēšanu un izmērīt, ko tā dod. Vārdu «viegls» darbā lietoju attiecībā uz konkrētu risinātāju, tā likumiem un atvēlēto laiku.

### 2. Ko mēra skeneris · 0:35–1:20

No 80 Latvijas olimpiāžu kandidātiem eksperimentā iekļāvu 65 ar pieņemtu formalizāciju. Teksta vietā risinātājs saņem punktu konstrukciju, dotās sakarības un pierādāmo apgalvojumu. Vispirms tas piemēro ģeometrijas likumus. Algebriskā spriešana papildus ļauj apvienot vienādojumus, piemēram, par leņķiem vai nogriežņu attiecībām. Ja mērķi vēl nevar secināt, divām no trim stratēģijām ir atļauts meklēt vienu jaunu punktu. Katrā mēģinājumā pēc datu ielādes meklēšanai dotas 60 sekundes.

### 3. Tie paši 65 uzdevumi · 1:20–2:05

Katra tabulas šūna aptver vienus un tos pašus uzdevumus. Katrā rindā atšķiras palīgpunktu meklēšanas stratēģija, bet starp abām kolonnām mainās algebriskā spriešana. Ieslēdzot to, katrā rindā izdevās iegūt 20 pierādījumus. Pārbaudot uzdevumu identifikatorus, redzams, ka sakrīt arī visi 20 uzdevumi. Ikreiz pietika ar sākotnēji ievadītajiem punktiem. Izslēdzot algebrisko spriešanu, pierādījumu skaits visās rindās bija nulle. Vēl vienā pārbaudē atstāju algebrisko spriešanu ieslēgtu, bet izslēdzu vienpadsmit ar trijstūru līdzību saistītus likumus. Ar atlikušajiem 59 likumiem dedukcija pierādīja 15 no tiem pašiem 65 uzdevumiem.

### 4. Olimpiādes uzdevums · 2:05–2:40

*Parādi punktus A, D un B, tad mediānu BE.* Punkts D sadala malu divu pret vienu attiecībā. Punkts E ir otras malas viduspunkts, tāpēc BE ir mediāna. Tā krustojas ar CD punktā F. Uzdevums ir pierādīt, ka arī F ir viduspunkts, šoreiz nogrieznim BE. Zīmējums palīdz ieraudzīt sakarību. Lai tā būtu patiesa katrā šādā trijstūrī, vajadzīgs pamatojums. [Oficiālais uzdevums un atrisinājumi, 1. lpp.](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/2020-2030/VOL_75_uzd_ATR_9_12_klase.pdf#page=1)

### 5. Divas viduslīnijas · 2:40–3:40

*Norādi uz T un trim vienādi atzīmētajiem posmiem.* Ņemsim T par AD viduspunktu. Tad AT, TD un DB ir vienādi, tāpēc D ir BT viduspunkts. Tagad skatāmies uz trijstūri ADC. Tā malu viduspunkti T un E nosaka viduslīniju, tātad TE ir paralēla CD. Pārejam uz iekrāsoto trijstūri BTE. Caur malas BT viduspunktu D iet taisne, kas paralēla TE. Tā otras malas vidū satiek BE, un šis krustpunkts ir F. Tātad BF ir vienāds ar FE. Formalizācijā T jau bija dots. Sākotnējam dzinējam radās kļūda, bet pēc labojuma dedukcija ieguva pierādījumu. Šis piemērs ir no atsevišķās atkārtotās pārbaudes. [Formalizācija un atkārtotais pierādījums](../../results/latvia-domains/#recovered-grade-9-proof)

### 6. Piedāvāt punktu un pabeigt pierādījumu · 3:40–4:35

Kreisajā pusē vērtēta modeļa prognoze 200 atliktos piemēros. 143 gadījumos atsauces palīgpunkts bija starp četriem piedāvājumiem. Pirmais piedāvājums sakrita 113 gadījumos. Labajā pusē pārbaudīju citu prasmi: vai ar piedāvāto konstrukciju risinātājs tiek līdz mērķim. Izmantoju divus uzdevumu krājumus un katrā atlasīju uzdevumus, kuros ar dedukciju vien nepietika. No 26 JGEX uzdevumiem modeļa konfigurācija pierādīja sešus, bet no 14 starptautiskās olimpiādes uzdevumiem – nevienu. Šajās pārbaudēs izmantots mazā modeļa pēdējais kontrolpunkts pēc 20 000 apmācības soļiem. [Prognozes un pierādījumi](../../results/local-cpu/)

### 7. Vai pierādījumu var izsekot · 4:35–5:25

Pārbaudīju arī to, ko lasītājs var secināt no izdrukātā pamatojuma. Divdesmit sākotnējo pierādījumu algebriskajā daļā bija 48 soļi. Četrpadsmit gadījumos secinājums izriet jau no pašā solī uzrakstītajiem vienādojumiem. Vēl desmit izdodas pamatot, pievienojot ziņas no sākotnējās konstrukcijas. Atlikušajiem 24 pārbaudē pietrūka konteksta. Tas ierobežo iespēju patstāvīgi pārbaudīt izdruku. Turpinājumā katram šādam solim būtu jāsaglabā arī iepriekšējo faktu identifikatori. [Soļu pārbaude un precīzas kategorijas](../../results/latvia-domains/paired-ar/)

### 8. Ko var secināt par grūtību · 5:25–6:20

Vai pēc risinātāja iznākuma varam spriest, cik grūti bija skolēniem? Salīdzināju visus sešus starptautiskās olimpiādes gadus, kam vietējā uzdevumu kopā bija divi atšķirīgi uzdevumi. Vienā gadā abus risināja viena dalībnieku grupa. Piemēram, 2015. gadā par trešo uzdevumu dalībnieki ieguva vidēji 0,65 punktus no septiņiem, bet par ceturto – 4,79. Dedukcija pierādīja ceturtā uzdevuma formalizāciju. Trijos no sešiem pāriem risinātājs pierādīja tieši vienu uzdevumu, un katrreiz tam bija augstāks arī dalībnieku vidējais vērtējums. Pārējos trijos pāros risinātāja iznākumi sakrita. Šie dati parāda gan gadījumus, kuros rezultāti saskan, gan nelielās izlases robežas. [Visi seši pāri un to avoti](../../results/local-cpu/imo/score-comparison.md)

## Iespējamie jautājumi

- **Kāpēc 390 mēģinājumi un tikai 65 uzdevumi?** Katru uzdevumu risināja ar trim stratēģijām un diviem algebriskās spriešanas iestatījumiem. Tas dod 65 × 3 × 2. Citās eksperimenta sērijās maina arī pieejamos ģeometrijas likumus.
- **Ko nozīmē nulle?** Šajos uzdevumos ar dotajiem punktiem, noteikumiem, dziļumu un laiku nevienā mēģinājumā pierādījums netika atrasts. Citi pierādīšanas paņēmieni un ilgāks meklēšanas laiks jāpārbauda atsevišķi.
- **Vai ir arī Latvijas skolēnu vērtējumi?** Diviem 2015./16. gada 9. klases uzdevumiem tie ir zināmi. Valsts olimpiādē vidējais bija 3,92 no desmit un risinātājs ieguva pierādījumu. Atklātajā olimpiādē vidējais bija 5,69, bet labotajam risinātājam beidzās laiks. Šīm sacensībām bija atšķirīgas dalībnieku grupas. [Avoti un mērījumi](../../results/latvia-audit/#official-item-scores-for-two-grade-9-problems)
- **Kurš atrada T?** Tas bija ietverts formalizācijas sākotnējā konstrukcijā. Mediānas galapunkts slaidā nosaukts par E un palīgpunkts par T, lai zīmējumu varētu lasīt kopā ar olimpiādes tekstu. Oficiālā pirmā risinājuma autori izvēlas citu palīgpunktu – nogriežņa CD viduspunktu G.
- **Vai Latvijā ar modeļa palīdzību ieguva papildu pierādījumus?** Pilno 70 likumu sākotnējā eksperimentā trīs stratēģiju atrasto uzdevumu kopas pilnīgi sakrita. Kombinētajā konfigurācijā 5,1 miljona parametru modelis `mid` darbojās kopā ar heiristikām. Sestā slaida atsevišķajos testos izmantots 11,2 miljonu parametru modelis `small`.
- **Kā pārbaudīta formalizācija?** Katrā no 65 uzdevumiem mēģināja uzbūvēt 64 zīmējumus ar jaunām nejaušības sēklām. Visos 3 940 sekmīgi uzbūvētajos zīmējumos mērķis izpildījās. Vēl 220 gadījumos konstrukciju neizdevās uzbūvēt. Atbilstība oficiālajam tekstam padziļināti pārbaudīta sešu uzdevumu izlasē. [Pārbaudes un atlases apraksts](../../results/latvia-audit/)

## Būvēšana

No repozitorija saknes palaid `make -C zpd_darbs PY="$(command -v python)" presentation` pēc projekta Python vides aktivizēšanas. Komanda atjauno [skaitliskos datus](dati.tex) no saglabātajiem mērījumiem un kompilē [rediģējamo avotu](prezentacija.tex) ar LuaLaTeX. Trijstūra [vektoru zīmējuma avots](../figures/median-diagram.tex) ir kopīgs slaidiem un darba pielikumam. Vajadzīgs fonts Liberation Sans. [TeX konteinera instrukcija](../README.md#build)

Lai pirms uzstāšanās pievienotu vārdu un darba vadītāju, blakus avotam izveido lokālu failu `tituldati.local.tex` ar komandām `\renewcommand{\autors}{...}` un `\renewcommand{\vaditajs}{...}`, pēc tam vēlreiz būvē PDF. Publicētā versija ietver skolu, pilsētu un gadu.
