from app.storyboard import split_sentences, template_storyboard

def test_split_sentences():
    assert split_sentences("First sentence. Second sentence!") == ["First sentence.", "Second sentence!"]

def test_template_storyboard_keeps_script():
    data = template_storyboard("A topic","This is the supplied script. Do not change it.","","cinematic","hinglish","short")
    assert data["generation_mode"] == "template"
    assert data["scenes"][0]["narration"] == "This is the supplied script."
    assert data["format"] == "short"
