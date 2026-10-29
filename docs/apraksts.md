Tēma: Olimpiāžu ģeometrijas uzdevumu skeneris vieglu risinājumu atrašanai vienā ģeometrijas jomā

Anotācija:
Darbā tiek izstrādāts rīks, kas automātiski pārskata olimpiāžu ģeometrijas uzdevumu kopu un katram uzdevumam nosaka, vai tam eksistē viegls risinājums noteiktā ģeometrijas jomā. Joma tiek definēta kā izvēlēta teorēmu (deduktīvo likumu) un konstrukciju kopa, piemēram, "trijstūri un riņķa līnijas bez līdzību teorēmām". Rīka pamatā ir AlphaGeometry pieeja: determinēts DD-AR dzinējs (Newclid) pierāda faktus, nekļūdoties, bet, ja tas apstājas, palīgpunktus piedāvā cilvēka heiristikas (viduspunkti, apvilktās riņķa līnijas centri, augstumu pamati) un paša apmācīts mazs transformeris. Risinājums tiek uzskatīts par vieglu, ja tas atrodams ar jomas likumiem, ne vairāk kā vienu palīgkonstrukciju un nelieliem resursiem. Rezultāts ir tabula, kurā katram uzdevumam norādīts, vai viegls risinājums atrasts, kāds tas ir, kuri likumi tajā izmantoti un cik daudz laika, atmiņas un deduktīvo soļu tas prasīja.

Ievads:
Olimpiāžu ģeometrijas uzdevumu krājumos grūtība parasti ir norādīta subjektīvi (pēc autora vai žūrijas vērtējuma), un nav redzams, kuri uzdevumi patiesībā atrisināmi ar vienas tēmas zināšanām. Skolotājiem un skolēniem būtu noderīgi zināt:
	- kuri uzdevumi atrisināmi tikai ar konkrētas jomas teorēmām (piemēram, tikai ar ievilktajiem leņķiem);
	- kuriem uzdevumiem nepieciešama viena "atslēgas" palīgkonstrukcija un kura tieši;
	- kuri uzdevumi šajā jomā nav viegli risināmi un prasa plašākas zināšanas.
Ar roku šādu analīzi veikt simtiem uzdevumu ir lēni un neprecīzi. AlphaGeometry tipa sistēmas ļauj to automatizēt, jo to pierādījumi ir pārbaudāmi soli pa solim un katra rīka (likumi, algebriskā spriešana, palīgpunktu ģenerators) ieguldījumu var kontrolēt atsevišķi.

Mērķis:
Izveidot un pārbaudīt rīku, kas olimpiāžu ģeometrijas uzdevumu kopā izvēlētai ģeometrijas jomai atrod uzdevumus ar vieglu risinājumu, parāda šos risinājumus un izmērāmi raksturo to vieglumu.

Uzdevumi (tā pati numerācija kā failā tasks):
Izstrāde (izpildīts):
	1. DD-AR dzinējs un jomas: Newclid DD-AR darbojas uz CPU; joma ir JSON konfigurācija ar ieslēgtajiem likumiem un AR slēdzi, ar brīdinājumiem, ja likumu kopa nevar izmantot vai pierādīt kādu predikātu.
	2. Palīgpunktu avoti: cilvēka heiristikas (viduspunkti, apvilktās riņķa līnijas centri, augstumu pamati) un mazs, no nulles uzrakstīts transformeris ar apmācības skriptu un 100 000 GenesisGeo piemēriem.
	3. Risinātājs: meklēšana "DD-AR, tad palīgpunkts, tad atkal DD-AR" ar dziļuma un zarošanās ierobežojumiem; funkcija solve(uzdevums, konfigurācija, resursi) atsevišķā procesā ar laika, atmiņas un CPU ierobežojumiem.
	4. Tulkošana un uzdevumu krātuve: vadlīnijas olimpiāžu uzdevumu tulkošanai Newclid sintaksē ar skaitlisku zīmējuma pārbaudi; krātuve ar katra uzdevuma rezultātiem dažādās jomās un ar dažādiem resursiem.
	5. Dokumentācija, testi un prezentācija.
Pētījums (vēl jāizpilda):
	6. Definēt 2-3 jomas (piemēram, tikai riņķa līnijas un ievilktie leņķi; viss, izņemot līdzīgos trijstūrus; ar AR un bez tā) un "viegluma" iestatījumu: dziļums ne vairāk kā 1, resursi 60 s un 2 GB.
	7. Pilnībā apmācīt transformeri un izmērīt, cik bieži tā piedāvātie palīgpunkti ir izmantojami un palīdz atrisināt uzdevumus.
	8. Savākt un pārtulkot olimpiāžu uzdevumus (piemēram, valsts olimpiādes, Baltic Way, IMO shortlist), pārbaudīt tos skaitliski un pierakstīt metadatus: avots, gads, tēma, oficiālā grūtība.
	9. Noskenēt visus uzdevumus visās jomās un saglabāt rezultātus.
	10. Analīze: katrā jomā noteikt uzdevumus ar vieglu risinājumu, atslēgas palīgkonstrukciju un viegluma rādītājus; salīdzināt jomas un palīgpunktu avotus; salīdzināt ar oficiālo grūtību un oficiālajiem risinājumiem; izpētīt uzdevumus, kuriem viegls risinājums netika atrasts.
	11. Noformēt rezultātus darbā un atjaunināt prezentāciju ar reāliem skaitļiem.

"Viegla risinājuma" definīcija:
Risinājums ir viegls izvēlētajā jomā, ja:
	- tas izmanto tikai jomas likumus (un AR, ja joma to atļauj);
	- tam vajag ne vairāk kā vienu palīgkonstrukciju (meklēšanas dziļums 0 vai 1);
	- tas atrasts dotajos resursos (piemēram, 60 s, 2 GB atmiņas).
Vieglumu raksturo arī pierādījuma soļu skaits, izmantoto likumu skaits un patērētie resursi. Jo mazāk, jo vieglāk.

Metode:
Uzdevumi tiek ar roku pārtulkoti Newclid sintaksē un pārbaudīti skaitliski: zīmējums tiek uzzīmēts vairākas reizes, un apgalvojumam jābūt patiesam katrā zīmējumā. Katram uzdevumam rīks:
	1. palaiž DD-AR tikai ar jomas likumiem; ja mērķis pierādīts, risinājumam nevajag palīgkonstrukcijas;
	2. ja DD-AR apstājas, lūdz palīgpunktus heiristikām un transformerim, katru pievieno un palaiž DD-AR vēlreiz;
	3. saglabā rezultātu: atrisināts vai nē, pierādījumu, palīgkonstrukciju, izmantotos likumus, meklēšanas dziļumu un patērēto laiku, atmiņu un CPU.
To pašu uzdevumu kopu var skenēt dažādās jomās (likumu kopās) un ar dažādiem resursiem. Visi rezultāti glabājas GitHub repozitorijā un ir atkārtojami.
Pierādījumu pareizību garantē DD-AR: tas lieto tikai zināmas teorēmas, un katrs solis ir pārbaudāms. Transformeris un heiristikas tikai piedāvā punktus, bet neko nepierāda.

Sagaidāmie rezultāti:
	- Atvērta pirmkoda rīks (Python, darbojas uz CPU), kas skenē uzdevumu mapi izvēlētā jomā un izdod rezultātu tabulu.
	- Katram uzdevumam: vai eksistē viegls risinājums, pats risinājums (soli pa solim), atslēgas palīgkonstrukcija un vieglumu raksturojošie skaitļi.
	- Jomu salīdzinājums: kuri uzdevumi kļūst atrisināmi, pievienojot konkrētu teorēmu vai algebrisko spriešanu.

Novērtēšana:
	- Pārbaudes kopa: 10 ar roku pārtulkoti olimpiāžu uzdevumi un Newclid uzdevumu kopas.
	- Mēri: atrasto vieglo risinājumu skaits, pierādījumu garums, patērētie resursi, palīgkonstrukciju avots (heiristika vai transformeris).
	- Salīdzinājums starp jomām un starp palīgkonstrukciju avotiem (bez palīgpunktiem, tikai heiristikas, heiristikas un transformeris).

Ierobežojumi:
	- Uzdevumi jātulko ar roku; rīks aptver tikai to, ko var izteikt ar Newclid konstrukcijām (plaknes ģeometrija: punkti, taisnes, riņķa līnijas, leņķi, attiecības).
	- Ja viegls risinājums netiek atrasts, tas nenozīmē, ka tāda nav: rīks meklē tikai ierobežotā telpā.
	- Mazais transformeris uz CPU apmācāms ilgi (apmēram 14 h); bez tā palīgpunktus piedāvā tikai heiristikas.
	- Likumu izslēgšana iespējama tikai Newclid Python dzinējā, kas ir lēnāks par C++ dzinēju (yuclid).

Pielietojums:
Skolotājiem un olimpiāžu sagatavotājiem: atlasīt uzdevumus konkrētai tēmai, atrast "vienas idejas" uzdevumus un parādīt, kura palīgkonstrukcija ir atslēga. Ilgtermiņā tas pats rīks var salīdzināt mācību programmas pēc tā, cik uzdevumu atrisināmi ar programmā apgūtajām teorēmām.
