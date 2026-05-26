@echo off
echo OPTCG Judge Trainer - Download all sets
echo ========================================
echo This will download ALL cards from OP01 to OP15 + ST + EB + PRB.
echo It will take approximately 45-60 minutes.
echo.
pause

echo --- Main Sets ---
python scripts/add_cards.py --set OP01
python scripts/add_cards.py --set OP02
python scripts/add_cards.py --set OP03
python scripts/add_cards.py --set OP04
python scripts/add_cards.py --set OP05
python scripts/add_cards.py --set OP06
python scripts/add_cards.py --set OP07
python scripts/add_cards.py --set OP08
python scripts/add_cards.py --set OP09
python scripts/add_cards.py --set OP10
python scripts/add_cards.py --set OP11
python scripts/add_cards.py --set OP12
python scripts/add_cards.py --set OP13
python scripts/add_cards.py --set OP14-EB04
python scripts/add_cards.py --set OP15-EB04

echo --- Extra Boosters ---
python scripts/add_cards.py --set EB01
python scripts/add_cards.py --set EB02
python scripts/add_cards.py --set EB03

echo --- Premium Boosters ---
python scripts/add_cards.py --set PRB01
python scripts/add_cards.py --set PRB02

echo --- Starter Decks ---
python scripts/add_cards.py --set ST01
python scripts/add_cards.py --set ST02
python scripts/add_cards.py --set ST03
python scripts/add_cards.py --set ST04
python scripts/add_cards.py --set ST05
python scripts/add_cards.py --set ST06
python scripts/add_cards.py --set ST07
python scripts/add_cards.py --set ST08
python scripts/add_cards.py --set ST09
python scripts/add_cards.py --set ST10
python scripts/add_cards.py --set ST11
python scripts/add_cards.py --set ST12
python scripts/add_cards.py --set ST13
python scripts/add_cards.py --set ST14
python scripts/add_cards.py --set ST15
python scripts/add_cards.py --set ST16
python scripts/add_cards.py --set ST17
python scripts/add_cards.py --set ST18
python scripts/add_cards.py --set ST19
python scripts/add_cards.py --set ST20
python scripts/add_cards.py --set ST21
python scripts/add_cards.py --set ST22
python scripts/add_cards.py --set ST23
python scripts/add_cards.py --set ST24
python scripts/add_cards.py --set ST25
python scripts/add_cards.py --set ST26
python scripts/add_cards.py --set ST27
python scripts/add_cards.py --set ST28

echo.
echo ========================================
echo All sets downloaded!
echo.
echo Next steps:
echo   1. git add .
echo   2. git commit -m "add all cards"
echo   3. git push
echo.
pause
