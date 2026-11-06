"""Offline Czech grammar reference. Each topic has text in Czech and English.

`keys` are accent-free stems (or phrases) used to match questions to topics.
"""

TOPICS = {
"vyjmenovana": {
 "keys": ["vyjmenovan", "pribuzn"],
 "title": {"cs": "Vyjmenovaná slova", "en": "Listed words (vyjmenovaná slova)"},
 "cs": "Po obojetných souhláskách (b, f, l, m, p, s, v, z) se v kořeni píše y/ý jen ve vyjmenovaných a příbuzných slovech, jinak i/í.\n"
       "B: být, bydlit, obyvatel, byt, příbytek, nábytek, dobytek, obyčej, bystrý, bylina, kobyla, býk, Přibyslav\n"
       "L: slyšet, mlýn, blýskat se, polykat, plynout, plýtvat, vzlykat, lysý, lýtko, lýko, lyže, pelyněk, plyš\n"
       "M: my, mýt, myslit, mýlit se, hmyz, myš, hlemýžď, mýtit, zamykat, smýkat, dmýchat, chmýří, nachomýtnout se, Litomyšl\n"
       "P: pýcha, pytel, pysk, netopýr, slepýš, pyj, kopyto, klopýtat, třpytit se, zpytovat, pykat, pýr, pýřit se, čepýřit se\n"
       "S: syn, sytý, sýr, syrový, sychravý, usychat, sýkora, sýček, sypat\n"
       "V: vy, vysoký, výskat, zvykat, žvýkat, vydra, výr, vyžle, povyk, výt, výheň\n"
       "Z: brzy, jazyk, nazývat se, Ruzyně",
 "en": "After the 'ambiguous' consonants (b, f, l, m, p, s, v, z), a word root takes y/ý only in the listed words and their relatives; otherwise i/í. Both sound identical, so it has to be memorised.\n"
       "B: být, bydlit, obyvatel, byt, příbytek, nábytek, dobytek, obyčej, bystrý, bylina, kobyla, býk, Přibyslav\n"
       "L: slyšet, mlýn, blýskat se, polykat, plynout, plýtvat, vzlykat, lysý, lýtko, lýko, lyže, pelyněk, plyš\n"
       "M: my, mýt, myslit, mýlit se, hmyz, myš, hlemýžď, mýtit, zamykat, smýkat, dmýchat, chmýří, nachomýtnout se, Litomyšl\n"
       "P: pýcha, pytel, pysk, netopýr, slepýš, pyj, kopyto, klopýtat, třpytit se, zpytovat, pykat, pýr, pýřit se, čepýřit se\n"
       "S: syn, sytý, sýr, syrový, sychravý, usychat, sýkora, sýček, sypat\n"
       "V: vy, vysoký, výskat, zvykat, žvýkat, vydra, výr, vyžle, povyk, výt, výheň\n"
       "Z: brzy, jazyk, nazývat se, Ruzyně",
},
"tvrde_mekke": {
 "keys": ["tvrd", "mekk", "souhlask", "psani i", "psani y"],
 "title": {"cs": "Tvrdé a měkké souhlásky", "en": "Hard and soft consonants"},
 "cs": "Tvrdé souhlásky (h, ch, k, r, d, t, n) → y/ý: chyba, kytka, ryba, hýbat.\n"
       "Měkké souhlásky (ž, š, č, ř, c, j, ď, ť, ň) → i/í: žito, číslo, cizí, šipka.\n"
       "U d, t, n rozhoduje výslovnost: dy/ty/ny zní tvrdě (dýchat, tykat, nyní), di/ti/ni měkce (divadlo, ticho, nic).\n"
       "Výjimky jsou hlavně slova přejatá: gramatika, text, politika.",
 "en": "Hard consonants (h, ch, k, r, d, t, n) → y/ý: chyba, kytka, ryba, hýbat.\n"
       "Soft consonants (ž, š, č, ř, c, j, ď, ť, ň) → i/í: žito, číslo, cizí, šipka.\n"
       "For d, t, n, pronunciation decides: dy/ty/ny sound hard (dýchat, tykat), di/ti/ni sound soft like ď/ť/ň (divadlo, ticho, nic).\n"
       "Exceptions are mostly loanwords: gramatika, text, politika.",
},
"koncovky_podst": {
 "keys": ["koncovk", "vzor", "podstatn"],
 "title": {"cs": "Koncovky podstatných jmen (vzory)", "en": "Noun endings (declension patterns)"},
 "cs": "Koncovku určíš podle rodu a vzoru.\n"
       "Rod mužský životný: pán, muž, předseda, soudce. Neživotný: hrad, stroj.\n"
       "Rod ženský: žena, růže, píseň, kost. Střední: město, moře, kuře, stavení.\n"
       "Tvrdé vzory mají v 1. p. mn. č. většinou -y/-a (hrady, ženy, města), měkké -e/-i (stroje, růže, muži). Pomůcka: dosaď slovo do vzoru ve stejném pádě a čísle.",
 "en": "The ending depends on the noun's gender and declension pattern.\n"
       "Masculine animate: pán, muž, předseda, soudce. Inanimate: hrad, stroj.\n"
       "Feminine: žena, růže, píseň, kost. Neuter: město, moře, kuře, stavení.\n"
       "Hard patterns usually have -y/-a in the nominative plural (hrady, ženy, města), soft ones -e/-i (stroje, růže, muži). Tip: put the pattern word in the same case and number and compare.",
},
"koncovky_prid": {
 "keys": ["pridavn", "mlady", "jarni", "otcuv", "matcin", "stupnovan"],
 "title": {"cs": "Přídavná jména", "en": "Adjectives"},
 "cs": "Tvrdá (vzor mladý): mladý muž, mladá žena, mladé dítě; mn. č. mladí muži, mladé ženy, mladá děvčata.\n"
       "Měkká (vzor jarní): stejný tvar jarní pro všechny rody v jednotném čísle.\n"
       "Přivlastňovací: otcův, matčin.\n"
       "Stupňování: 1. mladý, 2. mladší, 3. nejmladší. Nepravidelně: dobrý – lepší – nejlepší, zlý – horší – nejhorší.",
 "en": "Hard (pattern mladý): mladý muž, mladá žena, mladé dítě; plural mladí muži, mladé ženy, mladá děvčata.\n"
       "Soft (pattern jarní): the same form jarní for every gender in the singular.\n"
       "Possessive: otcův, matčin.\n"
       "Comparison: mladý – mladší – nejmladší. Irregular: dobrý – lepší – nejlepší, zlý – horší – nejhorší.",
},
"shoda": {
 "keys": ["shoda", "shod", "podmet s prisudk", "prisudk"],
 "title": {"cs": "Shoda přísudku s podmětem", "en": "Subject–verb agreement"},
 "cs": "Koncovka příčestí minulého v množném čísle závisí na rodu podmětu:\n"
       "mužský životný → -i: kluci běhali\n"
       "mužský neživotný → -y: stroje běžely\n"
       "ženský → -y: ženy zpívaly\n"
       "střední → -a: děvčata zpívala\n"
       "Více podmětů: je-li mezi nimi mužský životný, píše se -i (otec a matka šli); jinak většinou -y.",
 "en": "In the plural, the past participle's ending follows the subject's gender:\n"
       "masculine animate → -i: kluci běhali\n"
       "masculine inanimate → -y: stroje běžely\n"
       "feminine → -y: ženy zpívaly\n"
       "neuter → -a: děvčata zpívala\n"
       "With several subjects, any masculine animate one gives -i (otec a matka šli); otherwise usually -y.",
},
"me_mne": {
 "keys": ["mne"],
 "title": {"cs": "mě / mně", "en": "mě vs. mně"},
 "cs": "Zájmeno: mně ve 3. a 6. pádě (komu? o kom?), mě ve 2. a 4. pádě (koho?). Pomůcka: mně = komu (tobě), mě = koho (tebe).\n"
       "Dej mi to / dej mně to. Vidí mě. Mluví o mně.\n"
       "Ve slovech: mně píšeme tam, kde má příbuzné slovo n: zapomenout → zapomněl, vzpomenout → vzpomněl, domnívat se → domněnka. Jinak mě: město, měkký, měsíc, změna.",
 "en": "As a pronoun: mně in the dative and locative (to whom? about whom?), mě in the genitive and accusative (whom?). Tip: if tobě fits, write mně; if tebe fits, write mě.\n"
       "Dej mně to. Vidí mě. Mluví o mně.\n"
       "Inside words: mně where a related word has n: zapomenout → zapomněl, vzpomenout → vzpomněl, domnívat se → domněnka. Otherwise mě: město, měkký, měsíc, změna.",
},
"be_bje": {
 "keys": ["bje", "objekt"],
 "title": {"cs": "bě / bje", "en": "bě vs. bje"},
 "cs": "bje píšeme tam, kde se setká předpona ob- s kořenem na j: ob-jet → objet, ob-jem → objem, ob-jasnit → objasnit, ob-jednat → objednat, objekt.\n"
       "Jinak bě: oběd, oběť, běžet, oběhnout (ob + běhnout).",
 "en": "Write bje where the prefix ob- meets a root starting with j: ob-jet → objet, ob-jem → objem, objasnit, objednat, objekt.\n"
       "Otherwise bě: oběd, oběť, běžet, oběhnout (ob + běhnout).",
},
"ve_vje": {
 "keys": ["vje", "vjezd"],
 "title": {"cs": "vě / vje", "en": "vě vs. vje"},
 "cs": "vje píšeme, když se setká předpona v- s kořenem na j: v-jet → vjet, v-jezd → vjezd, v-jem → vjem.\n"
       "Jinak vě: věc, věda, květ, svět, věřit.",
 "en": "Write vje when the prefix v- meets a root starting with j: v-jet → vjet, v-jezd → vjezd, vjem.\n"
       "Otherwise vě: věc, věda, květ, svět, věřit.",
},
"s_z_predpony": {
 "keys": ["predpon", "predpona"],
 "title": {"cs": "Předpony s-, z-, vz-", "en": "Prefixes s-, z-, vz-"},
 "cs": "s- = pohyb dolů, z povrchu, dohromady: sběhnout, sejmout, sečíst, spojit.\n"
       "z- = změna stavu, dokonavost: zčervenat, zmrznout, zhasnout, změřit.\n"
       "vz- = pohyb vzhůru, vznik: vzlétnout, vzkvétat, vzpomenout.\n"
       "Pomůcka: význam, ne výslovnost. Předponu ověř podle významové řady.",
 "en": "s- = movement down, off a surface, or together: sběhnout, sejmout, sečíst, spojit.\n"
       "z- = change of state, completion: zčervenat, zmrznout, zhasnout, změřit.\n"
       "vz- = upward movement, coming into being: vzlétnout, vzkvétat.\n"
       "Decide by meaning, not by pronunciation.",
},
"s_z_predlozky": {
 "keys": ["predlozk", "predlozka"],
 "title": {"cs": "Předložky s, z", "en": "Prepositions s, z"},
 "cs": "s + 7. pád (s kým? s čím?): s kamarádem, se sestrou.\n"
       "z + 2. pád (odkud? z čeho?): ze školy, z lesa.\n"
       "Dvojtvar: se/ze před slovy, která začínají na stejnou nebo podobnou hlásku (se sestrou, ze zahrady).",
 "en": "s + instrumental (with whom/what): s kamarádem, se sestrou.\n"
       "z + genitive (from where/what): ze školy, z lesa.\n"
       "Use se/ze before words beginning with the same or a similar sound (se sestrou, ze zahrady).",
},
"u_krouzek": {
 "keys": ["krouzk", "carka nad"],
 "title": {"cs": "ú / ů", "en": "ú vs. ů"},
 "cs": "ú píšeme na začátku slova a po předponě: úkol, úterý, neúspěch, bezúročný.\n"
       "ů píšeme uprostřed a na konci slova: dům, stůl, kůň, bez domů.\n"
       "Výjimky: citoslovce a přejatá slova (múza, skútr, túra).",
 "en": "ú goes at the start of a word and straight after a prefix: úkol, úterý, neúspěch.\n"
       "ů goes in the middle and at the end: dům, stůl, kůň, bez domů.\n"
       "Exceptions: interjections and loanwords (múza, skútr, túra).",
},
"spodoba": {
 "keys": ["spodob", "znel", "neznel", "vyslovnost"],
 "title": {"cs": "Spodoba znělosti", "en": "Voicing assimilation"},
 "cs": "Párové souhlásky se ve výslovnosti přizpůsobují: b/p, d/t, ď/ť, g/k, h/ch, v/f, z/s, ž/š.\n"
       "Psaní ověříš tvarem, kde za souhláskou následuje samohláska: hrad → hradu (d), had → hada, tužka → tužek (ž), kapka → kapek.\n"
       "Na konci slova se znělá vyslovuje neznělá: dub [dup].",
 "en": "Paired consonants change in speech: b/p, d/t, ď/ť, g/k, h/ch, v/f, z/s, ž/š.\n"
       "To check spelling, find a form with a vowel after the consonant: hrad → hradu (d), tužka → tužek (ž), kapka → kapek.\n"
       "At the end of a word a voiced consonant is pronounced voiceless: dub [dup].",
},
"zdvojene": {
 "keys": ["zdvojen", "nn", "dvojit"],
 "title": {"cs": "Zdvojené souhlásky", "en": "Double consonants"},
 "cs": "Dvojité n vzniká na švu kořene a přípony: cena + ný → cenný, den + ní → denní, kámen + ný → kamenný.\n"
       "Jedno n, když kořen na n nekončí: hodný, jarní.\n"
       "Zdvojené je také v předponách: oddělit, rozzlobit, bezzubý, nejjasnější.",
 "en": "A double n appears where a root ending in n meets a suffix: cena + ný → cenný, den + ní → denní, kámen + ný → kamenný.\n"
       "Single n when the root doesn't end in n: hodný, jarní.\n"
       "Prefixes can double too: oddělit, rozzlobit, bezzubý, nejjasnější.",
},
"podminka_by": {
 "keys": ["aby", "kdyby", "podminovac", "bychom", "byste", "bych"],
 "title": {"cs": "by, aby, kdyby", "en": "by, aby, kdyby (conditional)"},
 "cs": "Tvary: já bych, ty bys, on by, my bychom, vy byste, oni by. Stejně aby: abych, abys, aby, abychom, abyste, aby; kdyby: kdybych, kdybys, kdyby, kdybychom, kdybyste, kdyby.\n"
       "Chybně: *bysme, *abysme, *kdybysme.\n"
       "Podmiňovací tvary se píší s y, protože patří ke slovesu být.",
 "en": "Forms: já bych, ty bys, on by, my bychom, vy byste, oni by. Same for aby: abych, abys, aby, abychom, abyste, aby; kdyby: kdybych, kdybys, kdyby, kdybychom, kdybyste, kdyby.\n"
       "Wrong: *bysme, *abysme, *kdybysme.\n"
       "They take y because they come from the verb být.",
},
"byt_bit": {
 "keys": ["byt ", "bit "],
 "title": {"cs": "být / bít, byt / bit", "en": "být vs. bít"},
 "cs": "být = existovat (jsem, byl, bytost); byt = obydlí; bít = tlouci (bije, bil, bitva, bitý).\n"
       "Rozhoduje význam: Byl doma. × Bil ho. Bydlí v bytě. × Hodiny bily.",
 "en": "být = to be (jsem, byl, bytost); byt = a flat; bít = to beat or strike (bije, bil, bitva).\n"
       "Meaning decides: Byl doma (he was home). × Bil ho (he hit him). Hodiny bily (the clock struck).",
},
"ji_ji": {
 "keys": ["jim", "ji "],
 "title": {"cs": "ji / jí, jim / jím, mi / my, vy / ví", "en": "ji/jí, mi/my, vy/ví"},
 "cs": "ji = 4. pád (vidím ji), jí = 2., 3., 6., 7. pád nebo tvar slovesa jíst (dám jí, jí oběd).\n"
       "mi = mně (dej mi), my = 1. os. mn. č. (my jdeme).\n"
       "vy = 2. os. mn. č. (vy jdete), ví = on ví (vědět).\n"
       "jim = komu? (dám jim), jím = kým? nebo já jím.",
 "en": "ji = accusative (vidím ji); jí = genitive, dative, locative, instrumental, or 'eats' (dám jí, jí oběd).\n"
       "mi = to me (dej mi); my = we (my jdeme).\n"
       "vy = you plural (vy jdete); ví = he/she knows (vědět).\n"
       "jim = to them (dám jim); jím = by him/it, or 'I eat'.",
},
"sebou": {
 "keys": ["sebou", "s sebou"],
 "title": {"cs": "sebou / s sebou", "en": "sebou vs. s sebou"},
 "cs": "s sebou = něco vezmu s sebou (mám u sebe): Vezmi si deštník s sebou.\n"
       "sebou = pohyb těla, zvratné 7. p.: trhnout sebou, praštit sebou.",
 "en": "s sebou = taking something along: Vezmi si deštník s sebou.\n"
       "sebou = a movement of the body, reflexive instrumental: trhnout sebou, praštit sebou.",
},
"velka_pismena": {
 "keys": ["pismen", "pismeno"],
 "title": {"cs": "Velká písmena", "en": "Capital letters"},
 "cs": "Velké písmeno: začátek věty, vlastní jména (Karel, Praha, Vltava), obyvatelé (Čech, Pražan), názvy institucí a svátků (Vánoce, Karlova univerzita).\n"
       "Malé: jazyky (čeština), dny a měsíce (pondělí, leden), přídavná jména (český).\n"
       "Ulice a náměstí: Na Příkopě, Václavské náměstí, ulice Dlouhá.",
 "en": "Capitalise: sentence starts, proper names (Karel, Praha, Vltava), inhabitants (Čech, Pražan), institutions and holidays (Vánoce, Karlova univerzita).\n"
       "Lower case: languages (čeština), days and months (pondělí, leden), adjectives (český).\n"
       "Streets and squares: Na Příkopě, Václavské náměstí, ulice Dlouhá.",
},
"carky": {
 "keys": ["cark", "interpunkc", "oddel"],
 "title": {"cs": "Čárky ve větě", "en": "Commas"},
 "cs": "Čárku píšeme mezi větami v souvětí, před spojky ale, avšak, však, proto, neboť, a to; před vedlejší větou (který, že, protože, když, aby), a kolem vsuvek a oslovení.\n"
       "Před a, i, ani, nebo čárka většinou není. Výjimka: poměr stupňovací nebo důsledkový (Byl unavený, a proto šel spát).\n"
       "Přístavek odděl z obou stran: Karel, můj bratr, přišel.",
 "en": "Use commas between clauses, before ale, avšak, však, proto, neboť, and a to; before subordinate clauses (který, že, protože, když, aby); and around parentheticals and direct address.\n"
       "Usually none before a, i, ani, nebo, except a consequence (Byl unavený, a proto šel spát).\n"
       "Set off an appositive on both sides: Karel, můj bratr, přišel.",
},
"prima_rec": {
 "keys": ["prima rec", "primou rec", "uvozovk", "uvozovac"],
 "title": {"cs": "Přímá řeč", "en": "Direct speech"},
 "cs": "Uvozovací věta před: Řekl: „Pojď sem.“\n"
       "Uvozovací věta za: „Pojď sem,“ řekl. / „Kam jdeš?“ zeptal se.\n"
       "Uvnitř: „Pojď,“ řekl, „půjdeme spolu.“",
 "en": "Reporting clause first: Řekl: „Pojď sem.“\n"
       "Reporting clause after: „Pojď sem,“ řekl. / „Kam jdeš?“ zeptal se.\n"
       "In the middle: „Pojď,“ řekl, „půjdeme spolu.“",
},
"pady": {
 "keys": ["pad", "padem", "skloňov", "sklonov", "sklonuj"],
 "title": {"cs": "Pády", "en": "The seven cases"},
 "cs": "1. kdo? co? (nominativ)\n2. (bez) koho? čeho? (genitiv)\n3. (ke) komu? čemu? (dativ)\n4. (vidím) koho? co? (akuzativ)\n5. oslovujeme, voláme (vokativ)\n6. (o) kom? čem? (lokál)\n7. (s) kým? čím? (instrumentál)",
 "en": "1. kdo? co? (nominative)\n2. (bez) koho? čeho? (genitive)\n3. (ke) komu? čemu? (dative)\n4. (vidím) koho? co? (accusative)\n5. direct address (vocative)\n6. (o) kom? čem? (locative)\n7. (s) kým? čím? (instrumental)",
},
"rod": {
 "keys": ["rod", "rodu", "zivotn", "neutrum", "femininum", "maskulinum"],
 "title": {"cs": "Mluvnický rod", "en": "Grammatical gender"},
 "cs": "Mužský životný (ten pán), mužský neživotný (ten hrad), ženský (ta žena), střední (to město). Pomůcka: dosaď ten / ta / to. Životnost zjistíš ve 4. p. mn. č.: vidím ty pány (životný), vidím ty hrady (neživotný).",
 "en": "Masculine animate (ten pán), masculine inanimate (ten hrad), feminine (ta žena), neuter (to město). Tip: try ten / ta / to. Check animacy with the accusative plural: vidím ty pány (animate), vidím ty hrady (inanimate).",
},
"slovni_druhy": {
 "keys": ["slovni druh", "ohebn", "neohebn"],
 "title": {"cs": "Slovní druhy", "en": "Parts of speech"},
 "cs": "Ohebné: 1. podstatná jména, 2. přídavná jména, 3. zájmena, 4. číslovky, 5. slovesa.\nNeohebné: 6. příslovce, 7. předložky, 8. spojky, 9. částice, 10. citoslovce.",
 "en": "Inflected: 1. nouns (podstatná jména), 2. adjectives (přídavná jména), 3. pronouns (zájmena), 4. numerals (číslovky), 5. verbs (slovesa).\nUninflected: 6. adverbs (příslovce), 7. prepositions (předložky), 8. conjunctions (spojky), 9. particles (částice), 10. interjections (citoslovce).",
},
"zajmena": {
 "keys": ["zajmen"],
 "title": {"cs": "Zájmena", "en": "Pronouns (zájmena)"},
 "cs": "Zastupují nebo blíže určují podstatná a přídavná jména. Druhy: osobní (já, ty), přivlastňovací (můj, svůj), ukazovací (ten, tento), tázací (kdo, co, jaký), vztažná (který, jenž), neurčitá (někdo, něco), záporná (nikdo, nic).",
 "en": "They stand in for nouns and adjectives. Types: personal (já, ty), possessive (můj, svůj), demonstrative (ten, tento), interrogative (kdo, co, jaký), relative (který, jenž), indefinite (někdo, něco), negative (nikdo, nic).",
},
"cislovky": {
 "keys": ["cislovk"],
 "title": {"cs": "Číslovky", "en": "Numerals (číslovky)"},
 "cs": "Základní: jeden, dva, pět. Řadové: první, pátý (5.). Druhové: dvojí, patery. Násobné: dvakrát, pětkrát.\nPo pět a výše stojí podstatné jméno ve 2. pádě: pět knih. Dva/tři/čtyři se shodují: dvě knihy.",
 "en": "Cardinal: jeden, dva, pět. Ordinal: první, pátý (5.). Kind: dvojí, patery. Multiplicative: dvakrát, pětkrát.\nFrom five up, the noun goes in the genitive: pět knih. Dva/tři/čtyři agree: dvě knihy.",
},
"slovesa": {
 "keys": ["sloves", "casov", "minul", "prit", "budouc", "infinitiv", "zpusob", "osob", "tvar slov"],
 "title": {"cs": "Slovesné kategorie", "en": "Verb categories"},
 "cs": "Osoba: 1. (já/my), 2. (ty/vy), 3. (on/oni). Číslo: jednotné, množné.\nČas: minulý (dělal jsem), přítomný (dělám), budoucí (budu dělat).\nZpůsob: oznamovací (dělá), rozkazovací (dělej), podmiňovací (dělal by).\nVid: dokonavý (udělat) a nedokonavý (dělat). Rod: činný (píše) a trpný (je psán).",
 "en": "Person: 1st (já/my), 2nd (ty/vy), 3rd (on/oni). Number: singular, plural.\nTense: past (dělal jsem), present (dělám), future (budu dělat).\nMood: indicative (dělá), imperative (dělej), conditional (dělal by).\nAspect: perfective (udělat) and imperfective (dělat). Voice: active (píše) and passive (je psán).",
},
"vid": {
 "keys": ["vid", "dokonav", "nedokonav"],
 "title": {"cs": "Slovesný vid", "en": "Verbal aspect"},
 "cs": "Dokonavý: děj ukončený, nemá přítomný čas, tvar přítomný znamená budoucnost (udělám = zítra). Nedokonavý: děj probíhající nebo opakovaný (dělám). Pomůcka: nedokonavé lze spojit s budu (budu dělat), dokonavé ne.",
 "en": "Perfective: a completed action; its present form means the future (udělám = I will finish). Imperfective: ongoing or repeated (dělám). Tip: only imperfective verbs combine with budu (budu dělat).",
},
"vetne_cleny": {
 "keys": ["vetn", "clen", "podmet", "prisudek", "predmet", "privlast", "doplnek", "prislovecn", "urceni"],
 "title": {"cs": "Větné členy", "en": "Sentence elements"},
 "cs": "Podmět: kdo? co? koná (Pes štěká).\nPřísudek: co dělá? (Pes štěká).\nPředmět: ptáme se pádem kromě 1. a 5. (čtu knihu).\nPřívlastek: jaký? který? čí? (červené auto).\nPříslovečné určení: kde, kdy, jak, proč (běží rychle).\nDoplněk: vztahuje se k podmětu i přísudku (přišel unavený).",
 "en": "Subject (podmět): who/what acts (Pes štěká).\nPredicate (přísudek): what it does (Pes štěká).\nObject (předmět): found by asking with a case other than 1 or 5 (čtu knihu).\nAttribute (přívlastek): what kind? which? whose? (červené auto).\nAdverbial (příslovečné určení): where, when, how, why (běží rychle).\nComplement (doplněk): relates to both subject and verb (přišel unavený).",
},
"souveti": {
 "keys": ["souvet", "vedlejsi vet", "hlavni vet", "vetu jednoduch", "veta jednoduch", "souradn", "podradn", "pomer"],
 "title": {"cs": "Věta a souvětí", "en": "Clauses and compound sentences"},
 "cs": "Věta jednoduchá má jeden přísudek, souvětí aspoň dva.\nSouřadné: věty jsou si rovnocenné (Prší a fouká).\nPodřadné: vedlejší věta závisí na hlavní (Vím, že prší).\nDruhy vedlejších vět: podmětná, předmětná, přívlastková, příslovečná, doplňková, přísudková.\nPoměry: slučovací, odporovací, stupňovací, vylučovací, důvodový, důsledkový.",
 "en": "A simple sentence has one predicate; a compound sentence (souvětí) has at least two.\nCoordinate: equal clauses (Prší a fouká).\nSubordinate: one clause depends on another (Vím, že prší).\nSubordinate clause types: subject, object, attributive, adverbial, complement, predicative.\nCoordinate relations: copulative, adversative, gradational, disjunctive, causal, consequential.",
},
"tvorba_slov": {
 "keys": ["kmen", "koren", "predpon", "pripon", "stavba slova", "slovotvorn", "odvozen"],
 "title": {"cs": "Stavba slova", "en": "Word structure"},
 "cs": "Slovo = předpona + kořen + přípona + koncovka, například pod-les-í.\nKořen je společný příbuzným slovům (les, lesní, podlesí). Koncovka se při skloňování mění, kmen ne.",
 "en": "A word = prefix + root + suffix + ending, as in pod-les-í.\nThe root is shared by related words (les, lesní, podlesí). The ending changes in declension; the stem doesn't.",
},
"gap_general": {
 "keys": [],
 "title": {"cs": "Doplňovací cvičení", "en": "Fill-in exercise"},
 "cs": "Postup: 1. Urči slovní druh chybějícího slova. 2. Zjisti pád a číslo podle okolních slov (předložka, sloveso). 3. Dosaď vzor. Sloveso se shoduje s podmětem.",
 "en": "Steps: 1. Work out which part of speech is missing. 2. Find its case and number from the words around it (preposition, verb). 3. Use the matching declension pattern. A verb agrees with its subject.",
},
}
