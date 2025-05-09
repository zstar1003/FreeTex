#!/bin/bash

pyftsubset NotoSerifSC-VariableFont_wght.ttf \
    --text-file=../../../dev/chinese-3500.txt \
    --text-file=../../../dev/chinese-punctuations.txt \
    --output-file=NotoSerifSC-VariableFont_wght_3500_punc.ttf
woff2_compress NotoSerifSC-VariableFont_wght_3500_punc.ttf
rm NotoSerifSC-VariableFont_wght_3500_punc.ttf
