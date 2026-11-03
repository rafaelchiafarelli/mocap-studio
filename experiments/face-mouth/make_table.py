"""Writes the Portuguese phoneme table for Parrot: every phone the recognizer can output goes to one of 12 mouth poses."""
import json, sys, unicodedata
G = {
 "M": "b bʲ bʲj bʷ bʼ bː b̞ b̤ b̥ p pʰ pʲ pʲj pʷ pʷʼ pʼ pː p̚ m mʲ mʲj mʷ mː ɓ ŋ͡m k͡p̚",
 "F": "f fʲ fʷ fː v vʲ vʷ vː v̞ v̞ʲ ʋ ʋʲ ɸ β β̞ pf ɱ",
 "T": "t tʰ tʲ tʷʼ tʼ tː t̚ t̪ t̪ʰ t̪̚ d dʲ dː d̚ d̥ d̪ d̯ n nj nʲ nː n̪ n̺ ɳ ɲ ɖ̤ ɗ ʈ θ ð ɟ c",
 "S": "s sʲ sʼ sː s̪ z zj zʲ z̪ ts tsʰ t͡s t͡sʼ d͡z ç çj t͡ɬ",
 "SH": "ʃ ʃʲː ʃ͡ɣ ʒ ʒ͡ɣ ʂ ʐ ɕ ɕː ʑ dʒ tɕ tɕʰ tʂ tʂʰ tʃ t͡ɕ t͡ʃ t͡ʃʲ t͡ʃʼ t͡ʃː d͡ʑ d͡ʒ d͡ʒː d͡ʒ̤",
 "L": "l lʲ lː l̪ ɫ ʎ ɾ ɾj ɾʲ ɾ̠ ɽ r rː ɹ ɹ̩ ɻ ɻ̩",
 "K": "k kx kʰ kʲ kʲj kʷ kʷʼ kʼ kː k̟ʲ k̟̚ g gʲ gʲj gʷ gː ɡ ɡʲ ɡ̤ ɡ̥ q x x̟ʲ χ ɣ ɣj ʁ ʁ̝ ʀ h hʷ ɦ ŋ ŋ̟ ɴ ʔ ɰ ʝ",
 "A": "a aː ã ă ä æ ɐ ɐ̞ ɑ ɑ̱ ɒ ʌ ḁ ɤɐ̞",
 "E": "e eː e̞ ɛ ɛ̃ ə ә ɵ ɨ ø œ œ̃ ɤ ɤ̆ ː",
 "I": "i ij iː i̞ i̥ i̯ j I ɪ y ʏ ɥ",
 "O": "o oː o̞ o̥ ɔ ɔ̃",
 "U": "u uː u͡w uə w ʊ ʉ̞ ɯ ɯ̟ ɯ̥",
}
inv = [l.split()[0] for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
nfc = {unicodedata.normalize("NFC", c): c for c in inv}  # the recognizer's spelling of composed vowels
phones = [{"code": nfc.get(unicodedata.normalize("NFC", c), c), "class": g, "example": "", "group": g} for g, s in G.items() for c in s.split()]
codes = [p["code"] for p in phones]
print("inventory", len(inv), "mapped", len(set(codes)), "missing", sorted(set(inv) - set(codes)), "extra", sorted(set(codes) - set(inv)), "dupes", len(codes) - len(set(codes)))
json.dump({"info": {"note": "Portuguese mouth groups; test table"}, "groups": [{"name": g, "description": s} for g, s in G.items()], "phonemes": phones}, open(sys.argv[2], "w", encoding="ascii"), ensure_ascii=True, indent=1)  # Parrot opens the table with the system encoding
