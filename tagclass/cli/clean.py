import typer
from rich import print
from tagclass.common import (
    FAMILY_VOC_FILE,
    LOCATOR_VOC_FILE,
    MISC_VOC_FILE,
    INIT_LOCATOR_VOC_FILE,
    INIT_MISC_VOC_FILE,
)
from tagclass.tag import Vocabulary, LOCATORS

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    init: bool = False,
    sort: bool = False,
):

    if init:
        locator_voc_file = INIT_LOCATOR_VOC_FILE
        misc_voc_file = INIT_MISC_VOC_FILE
    else:
        locator_voc_file = LOCATOR_VOC_FILE
        misc_voc_file = MISC_VOC_FILE

    def clean_locator():
        locvoc = Vocabulary([locator_voc_file], unconfirmed_ok=True)
        locvoc.dump(LOCATORS, locator_voc_file, sort=sort)

    def clean_family():
        locvoc = Vocabulary([LOCATOR_VOC_FILE], unconfirmed_ok=True)
        famvoc = Vocabulary([FAMILY_VOC_FILE], unconfirmed_ok=True)
        for k, _ in locvoc.value.items():
            if famvoc.hit(k):
                del famvoc.value[k]
        famvoc.dump(['family'], FAMILY_VOC_FILE, sort=sort)

    def clean_misc():
        locvoc = Vocabulary([locator_voc_file], unconfirmed_ok=True)
        modvoc = Vocabulary([misc_voc_file], unconfirmed_ok=True)
        for k, _ in locvoc.value.items():
            if modvoc.hit(k):
                del modvoc.value[k]
        for k, v in modvoc.value.items():
            v.path = ''
        modvoc.dump(['misc'], misc_voc_file, sort=sort)

    if init:
        clean_locator()
        clean_misc()
        print('Finish clean init_voc unconfirmed.')
    else:
        clean_locator()
        clean_misc()
        clean_family()
        print('Finish clean voc unconfirmed.')