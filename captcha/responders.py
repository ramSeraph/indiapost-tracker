import re

class UnknownCaptchaTypeException(Exception):
    pass

class CaptchaParsingException(Exception):
    pass


nums = '1234567890'
smalls = 'abcdefghijklmnopqrstuvwxyz'
nums_and_smalls = nums + smalls
math_ops = '+-'

def filt(text, expected):
    out_text = ''
    for ch in text:
        if ch not in expected:
            continue
        out_text += ch
    return out_text
 

def fix(text, expected, bbox):
   
    if len(text) > 1:
        return text

    ch = ''
    if len(text) != 0:
        ch = text[0]

    _, _, w, h = bbox
    if expected == math_ops:
        if ch == '' or ch not in math_ops:
            if h < 15:
                ch = '-'
            else:
                ch = '+'
    return ch

CONF_THRESH = 80

class Responder:
    def __init__(self, tess_api_new, tess_api_old, imgs, bboxes):
        self.imgs = imgs
        self.bboxes = bboxes
        self.tess_api_new = tess_api_new
        self.tess_api_old = tess_api_old
        self.expected_num_chars = -1
        self.expected_chars = None
        self.to_log = []

    def answer(self):
        if len(self.imgs) != self.expected_num_chars:
            raise CaptchaParsingException(f'expected {self.expected_num_chars} pieces, got {len(self.imgs)} pieces')
        return self.evaluate()

    def evaluate(self):
        raise NotImplementedError()

    def getNth(self, i):
        try:
            text = self.getNthWithApi(i, self.tess_api_new)
        except CaptchaParsingException:
            text = self.getNthWithApi(i, self.tess_api_old,
                                      try_fixes=True, check_confidence=False)
        return text

    def getNthWithApi(self, i, api, try_fixes=False, check_confidence=True):
        img = self.imgs[i]
        expected = self.expected_chars[i]
        api.SetVariable('tessedit_char_whitelist', expected)
        api.SetImage(img)
        text = api.GetUTF8Text().strip()
        confidence = api.MeanTextConf()
        self.to_log.append((i, text, confidence))
        api.Clear()
        text = filt(text, expected)
        if try_fixes:
            text = fix(text, expected, self.bboxes[i])
        if len(text) != 1:
            raise CaptchaParsingException(f'got text="{text}" while detecting char at index: {i}')
        ch = text[0]
        if ch not in expected:
            raise CaptchaParsingException(f'got ch="{ch}" while detecting char at index: {i}, not in expected="{expected}"')
        if check_confidence and confidence < CONF_THRESH:
            raise CaptchaParsingException(f'got ch="{ch}" while detecting char at index: {i}, confidence low: {confidence} < {CONF_THRESH}')
        return ch



class EnterCharsResponder(Responder):
    def __init__(self, *args):
        super(EnterCharsResponder, self).__init__(*args)
        self.expected_num_chars = 6
        self.expected_chars = [nums_and_smalls]*6
    
    def evaluate(self):
        ans = ''
        for i in range(self.expected_num_chars):
            ans += self.getNth(i)
        return ans


class EvaluateExpressionResponder(Responder):
    def __init__(self, *args):
        super(EvaluateExpressionResponder, self).__init__(*args)
        self.expected_num_chars = 4
        self.expected_chars = [ nums, math_ops, nums, '=' ]

    def evaluate(self):
        num1 = int(self.getNth(0))
        num2 = int(self.getNth(2))
        op = self.getNth(1)
        if op == '+':
            return f'{num1 + num2}'
        if op == '-':
            return f'{num1 - num2}'


class EnterNthNumberResponder(Responder):

    def __init__(self, *args):
        idx = args[-1]
        args = args[:-1]
        super(EnterNthNumberResponder, self).__init__(*args)
        self.idx = idx
        self.expected_num_chars = 5
        self.expected_chars = [nums]*5

    def evaluate(self):
        return self.getNth(self.idx)


def get_responder_builder(label_text):
    nth_number_names = [ "First", "Second", "Third", "Fourth", "Fifth" ]
    nth_number_label_regex = rf'Enter the ({"|".join(nth_number_names)}) number'
    evaluate_label = 'Evaluate the Expression'
    enter_chars_label = 'Enter characters as displayed in image'

    if label_text == enter_chars_label:
        return EnterCharsResponder, []
    if label_text == evaluate_label:
        return EvaluateExpressionResponder, []
    match = re.match(nth_number_label_regex, label_text)
    if not match:
        raise UnknownCaptchaTypeException(label_text)
    nth = match.group(1)
    idx = nth_number_names.index(nth)
    if idx == -1:
        raise UnknownCaptchaTypeException(label_text)
    return EnterNthNumberResponder, [idx]
 
def get_responder(label_text, imgs, bboxes, tess_api_new, tess_api_old):
    ResponderCls, args = get_responder_builder(label_text)
    responder = ResponderCls(tess_api_new, tess_api_old, imgs, bboxes, *args)
    return responder

