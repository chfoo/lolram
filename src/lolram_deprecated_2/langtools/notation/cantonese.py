# encoding=utf8

# IPA, jyutping, yale
INITIALS = [
	(u'p', 'b', 'b'),
	(u'pʰ', 'p', 'p'),
	(u'm', 'm', 'm'),
	(u'f', 'f', 'f'),
	(u'd', 'd', 'd'),
	(u'tʰ', 't', 't'),
	(u'n', 'n', 'n'),
	(u'l', 'l', 'l'),
	(u'k', 'g', 'g'),
	(u'kʰ', 'k', 'k'),
	(u'ŋ', 'ng', 'ng'),
	(u'h', 'h', 'h'),
	(u'kʷ', 'gw', 'gw'),
	(u'kʷʰ', 'kw', 'kw'),
	(u'w', 'w', 'w'),
	(u'ts', 'z', 'j'),
	(u'tsʰ', 'c', 'ch'),
	(u's', 's', 's'),
	(u'j', 'j', 'y'),
]

FINALS = [
	(u'aː', 'aa', 'a'),
	(u'aːi', 'aai', 'aai'),
	(u'aːu', 'aau', 'aau'),
	(u'aːm', 'aam', 'aam'),
	(u'aːn', 'aan', 'aan'),
	(u'aːŋ', 'aang', 'aang'),
	(u'aːp', 'aap', 'aap'),
	(u'aːt', 'aat', 'aat'),
	(u'aːk', 'aak', 'aak'),
	(u'ɐi', 'ai', 'ai'),
	(u'ɐu', 'au', 'au'),
	(u'ɐm', 'am', 'am'),
	(u'ɐn', 'an', 'an'),
	(u'ɐŋ', 'ang', 'ang'),
	(u'ɐp', 'ap', 'ap'),
	(u'ɐt', 'at', 'at'),
	(u'ɐk', 'ak', 'ak'),
	(u'ɛː', 'e', 'e'),
	(u'ei', 'ei', 'ei'),
	(u'ɛːu', 'eu', 'eng'),
	(u'ɛːm', 'em', None),
	(u'ɛːŋ', 'eng', None),
	(u'ɛːp', 'ep', None),
	(u'ɛːk', 'ek', 'ek'),
	(u'iː', 'i', 'i'),
	(u'iːu', 'iu', 'iu'),
	(u'iːm', 'im', 'im'),
	(u'iːn', 'in', 'in'),
	(u'ɪŋ', 'ing', 'ing'),
	(u'iːp', 'ip', 'ip'),
	(u'iːt', 'it', 'it'),
	(u'ɪk', 'ik', 'ik'),
	(u'ɔː', 'o', 'o'),
	(u'ɔːi', 'oi', 'oi'),
	(u'ou', 'ou', 'ou'),
	(u'ɔːn', 'on', 'on'),
	(u'ɔːŋ', 'ong', 'ong'),
	(u'ɔːt', 'ot', 'ot'),
	(u'ɔːk', 'ok', 'ok'),
	(u'uː', 'u', 'u'),
	(u'uːi', 'ui', 'ui'),
	(u'uːn', 'un', 'un'),
	(u'ʊŋ', 'ung', 'ung'),
	(u'uːt', 'ut', 'ut'),
	(u'ʊk', 'uk', 'uk'),
	(u'œː', 'oe', 'eu'),
	(u'œːŋ', 'oeng', 'eung'),
	(u'œːk', 'oek', 'euk'),
	(u'ɵy', 'eoi', 'eui'),
	(u'ɵn', 'eon', 'eun'),
	(u'ɵt', 'eot', 'eut'),
	(u'yː', 'yu', 'yu'),
	(u'yːn', 'yun', 'yun'),
	(u'yːt', 'yut', 'yut'),
	(u'm̩', 'm', 'm'),
	(u'ŋ̩', 'ng', 'ng'),
]

# levels, jyutping, yale
TONES = [
	(u'˥˥', 1, 1),
	(u'˧˥', 2, 2),
	(u'˧˧', 3, 3),
	(u'˨˩', 4, 4),
	(u'˩˧', 5, 5),
	(u'˨˨', 6, 6),
	(u'˥', 1, 7),
	(u'˧', 3, 8),
	(u'˨', 6, 9),
]

initials_map = {}
finals_map = {}
tones_map = {}

for ipa, jyutping, yale in INITIALS:
	initials_map[jyutping] = (ipa, yale)

for ipa, jyutping, yale in FINALS:
	finals_map[jyutping] = (ipa, yale)

for ipa, jyutping, yale in TONES:
	tones_map[jyutping] = (ipa, yale)

def jyutping_split(s):
	i = 1
	
	initial = initials_map.get(s[0:1])
	
	if not initial:
		i += 1
		
	
