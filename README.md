# Mechanical display Flip-Flap

## About
Flip-Flap is an *Open Source* Mechanical Split Flap Display, AKA *Solari* display.

There are 2 versions. One for using an Arduino microcontroller and another for using a custom networked stepper board.

## Instructions and documentation
You have probably seen mechanical Split-Flap displays, they are usually located at airports and train stations all over the world. Their sound and movement are very characteristic. They are also called Solari boards because of the italian maker [Solari Udine](http://www.solari.it/index.php). I love these displays but the problem is that they are **extremely** expensive.

![solari](solari.jpg)

## Goal

The goal of the Flip-Flap project is to create a cheap and modular Open Source Mechanical Solari-like display. This project has been presented at the second edition of [Maker Faire Rome](http://www.makerfairerome.eu/) and shows the advantages and skills that you can learn taking the [Fab Academy](http://fabacademy.org) course (based on MIT’s How to Make Almost Anything). This is by far, the most advanced digital fabrication course in the world. If you want to make a living from digital fabrication, invest in your education.

![branding](branding.png)

## License

The Flip-Flap project is licensed open source hardware and software under [MIT](http://opensource.org/licenses/MIT) license.

## Who has done it beforehand?

I found some people researching and doing DIY split-flap displays but I could not manage to find files and instructions to assemble one.

*   [Unknown Domain](http://unknowndomain.co.uk/) is the most complete. It is a blog especifically talking about split-flap displays. It has tons of information
*   [Dearly Departures](https://www.indiegogo.com/projects/dearly-departures) is an Indiegogo crowdfunding campaign featuring a modular split-flap display

## Design overview

There will be 2 versions depending on the number of characters. This number is not arbitrary and it has been chosen to obtain an integer number of motor steps per character.

### Numerical version

This is a version for clocks, price display, showing temperature and humidity and counters. The number of characters of this version is 20 (space, 10 numbers, dot, comma, dash, euro, dollar, colon, degree, slash, percentage)

`0123456789.,-€$:º/%`

360º/20=18º per character  
Usual stepper motor has 1.8 degrees/step  
18/1.8º=10 steps per character

### Alphanumerical version

This is a version for displaying general text and the one I am bringing to Rome in the second edition of the Maker Faire Rome. The number of characters for this version is 40 (space, 26 letters, 10 numbers, dot, colon, euro)  
`ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:€`

360º/40=9º per character  
Motor has 1.8 degrees/step  
9/1.8º=5 steps per character

## Materials and parts

For the split cards I saw some people using cheap 30 mill black PVC cards, but I am going to replace it with 0.5 mm matte black and white Plakene® sheets (a commercial brand of polypropylene). Those sheets come in 75×105 cm size. PVC cannot be cut with the laser, not only for the toxic chlorines but also it will corrode everything inside your laser, and I don’t feel like manually cutting anything. A note on lasercutting polypropylene: It’s not easy because it does not vaporize, it melts and the borders hold the heat for long time. So if you put enough power to cut it in one pass, it slowly flows back to the gap and gets solded again. Black polypropylene cuts much better and with nicer border than white polypropylene. I used the following settings for cutting the 0.5 mm polypropylene sheets with the Full Spectrum 5th Gen 45W:

Power: 77  
Speed: 100  
Measured Kerf: 0.23 mm (but not taken into account)

The lettering is just white (or black) adhesive vinyl cut with the Roland Vinyl cutter. I am using white letters with a black background, but other cool color combinations are white cards/black letters, yellow cards/black letters and black cards/yellow letters, as you can see in the image below.

![colors](colors.png)

When you load the png in [fab modules](http://kokompe.cba.mit.edu/) you need to cut the letters in two steps. One for the letters (make .path with intensity 0.5) and another for the squares (make .path with intensity 1). You need to cut the squares too because that way it will be easier to align the letters on the cards.

![vinyl-letters](vinyl-letters-1024x559.png)  
![vinyl-cutouts](vinyl-cutouts-1024x559.png)

> NOTE: The settings you see of 45g of force and 5 cm/s of speed are the recommended ones by Neil. But I usually use 80g of force and up to 20 cm/s of speed depending upon the tired I am.

The mechanical transmission will consist in a lasercut or 3D printed gear set, that way the module will be thinner than the belt transmission system (and cheaper).

The container that hosts all the mechanical parts and electronics is a transparent press-fit box made in acrilic. It is transparent because I want people in Maker Faire Rome see how it works. Probably in a real installation I would use an opaque color. And it is a press-fit design because in words of our beloved Neil Gershenfeld: “Glue is a sign of failure”, and also because I will probably have to assemble and disassemble the box a lot at the beginning. Each module box connects with the other modules through magnets that carry power and data. The advantage of this solution is that it does not require any wires between the modules, data and power is transferred by contact and you can easily add and remove modules, even with power applied.

You will need a stepper motor, a small Jameco will do, and some electronics parts from the Fab Lab inventory.

## Electronics

If you look at the solutions out there, you will see almost everyone using an Arduino (25 EUR) or even an Arduino Mega (50 EUR) with an easydriver stepper driver (16 EUR). In [Fab Academy](http://fabacademy.org) you will learn how to design and fabricate a single board, with the same features, that cost around 3 EUR in components.

Each module is controlled with a hybrid electronic board which is a networked attiny44 microcontroller with an embedded stepper driver (a couple of H-bridges). There are two advantages of this design over other solutions I have seen. The first one is that each module is autonomous, it does not need any other microcontroller or computer (but you can always do so if you want). The second advantage is that it it only requires four wires between the modules, two for data and two for power.

This board has been designed in [kokopelli](https://github.com/mkeeter/kokopelli) (look mom, no Eagle!). Kokopelli was developed by Matt Keeter at MIT and it is a multi purpose design tool. You can design from circuit boards to mechanical parts and even control machines of the fab lab. And the best thing is that the design of the circuit board is python code written in a text editor.

![stepper](stepper.png)

This can be milled in a single side FR1 copper board with a Roland Modela and stuffed with SMD components from the official Fab Lab inventory.

# The spool and gears

I did not realise initially that this is a key part of the design. The perforated side spool size depends upon the number of characters. I decided that each hole would measure 3 mm in diameter with a distance between holes of about 1mm. Don’t increase the later distance much more than that, otherwise both half-letters will be too much separated. [Kokopelli](https://github.com/mkeeter/kokopelli) was used to design the wheel because it is very poweful. It took only a few lines of code and it is fully parametrical (check the files at the bottom).

![gears](gears.png)

The spool and gears were cut in black acrylic and the stiffners in orange fluor (they avoid torsional movement of the spool) with the laser cutter at 20% of speed and 100% of power (Full Spectrum 5th Gen settings). Those stiffners are now solid because the triangulated design broke easily.

[![spool](IMG_20140924_1925071.jpg)

## Split cards

### Size

At the beginning I had several doubts about size and proportions. Initially I decided to build 10×20 cm modules. But that was way too big for bringing it in the suitcase to Rome. I would like to bring some clothes also, if you don’t mind. So I analized and measured the above WARSAW LONDON image and found that the proportions were about 0.67, suspiciously close to the golden rectangle ratio 0.618\. So I decided that the final design size for Rome would be 86×54 mm which is exactly the size of the ISO CR80 standard credit card. It is a readable size and small enough for carrying several modules in the suitcase.

### Shape

If you look at other people’s designs you will notice they are making a strange shape with a gap on the sides, like the top image of this page. Unless you are going to make a very slim version of the split flap display, and you really need to save the space of the wheels there is no need to do that, specially if you are cutting by hand. Do not worry, the cards will not fall inside the wheels, they self-lock tangent to the next hole. The shape used in this project is a rectangle 55×43 mm with two small slots (3mm width and 4mm long) on the sides.

![card](card.png)

### Typeface

I asked Tom Lynch from [Unknown Domain](http://unknowndomain.co.uk/) if he knew the original typeface, but he didn’t. So again I analyzed the above image (WARSAW LONDON) with [Whatthefont](https://www.myfonts.com/WhatTheFont/) and I found that the closest one was [Blue Highway Bold](http://typodermicfonts.com/blue-highway-5-0/) by Larabie, which seems to be free for desktop use, so this is the one I am using for this project. Still is not the same, the W character for example is wider than the original Solari Typeface so I manually modified it in Inkscape.

![fsl-720-30](fsl-720-30.png)

UPDATE: I received an email from someone called MC, pointing out that the original Solari typeface is [Akzidenz-Grotesk Medium](http://www.bertholdtypes.com/font/akzidenz-grotesk/proplus/). If you carefully examine the glyphs, that appears to be correct, at least a custom variant of this font, as you can see in the image below. Thank you for the information MC.

![font-preview-1.ashx](font-preview-1.ashx_.png)

### Placing the stickers and the cards

Now you have to place the stickers in the split cards. That seems complicated since letters are splitted in different cards, but it is not. You just have to follow some simple rules and be faithful. The first thing you need to know is the order of your letters, in my case:

`ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:€`

Please note that the last character is a space (no sticker). You start by placing 2 cards (top and bottom) in front of you and putting the stickers for the first character A, then you flip down the top A card and place it next to the bottom A card, to the right. And then place a new empty card above it. Now you can put the stickers for letter B. Again grab the top B card, flip it down and place it next to bottom B card, to the right always. Repeat this for all the characters. You will end up with all the lower part of the cards in order. Now you can put them on the wheel one by one, with the module in normal looking position, you place lower-A, then lower-B in the next hole above and so on.

![letters](letters.jpg)

## Software

For Maker Faire Rome we brought an Arduino version instead of the final design because we run out of time. John Rees did all the coding in between beers and nutella sandwitches. He also wrote a ruby script that displays the current time, watch the video below:

<iframe width="853" height="480" src="/web/20150502224732if_/http://www.youtube.com/embed/5jPlX7p77Pk" frameborder="0" allowfullscreen=""></iframe>

## Project files

You can download all the files related to the Flip Flap project in our [Github](https://github.com/thebeachlab), please feel free to download, fork, modify and improve it.

For more (actually less) information about this project visit: http://beachlab.org/
