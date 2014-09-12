
/*
   Netskrafl.js
   Client-side script for the Netskrafl server in netskrafl.py

   Author: Vilhjalmur Thorsteinsson, 2014
   
*/

   function placeTile(sq, tile, letter, score) {
      if (tile.length == 0) {
         /* Erasing tile */
         $("#"+sq).html("");
         return;
      }
      if (sq.charAt(0) == "R") {
         /* Placing a tile into the rack */
         attr = "class='tile racktile' draggable='true'";
         letter = (tile == "?") ? "&nbsp;" : tile;
      }
      else
         /* Normal board tile */
         attr = "class='tile'";
      $("#"+sq).html("<div " + attr + ">" + letter +
         "<div class='letterscore'>" + score + "</div></div>");
      if (sq.charAt(0) == "R") {
         /* Store associated data with rack tiles */
         $("#"+sq).children().eq(0).data("tile", tile);
         $("#"+sq).children().eq(0).data("score", score);
      }
      else
      if (tile == '?') {
         /* Blank tile used as a letter: use different foreground color */
         $("#"+sq).children().eq(0).addClass("blanktile");
      }
   }

   function appendMove(player, coord, word, score) {
      /* Add a move to the move history list */
      wrdclass = "wordmove";
      if (coord == "") {
         /* Not a regular tile move */
         wrdclass = "othermove";
         if (word == "PASS")
            /* Pass move */
            word = "Pass";
         else
         if (word.indexOf("EXCH") == 0) {
            /* Exchange move */
            numtiles = parseInt(word.slice(5));
            word = "Skipti um " + numtiles.toString() + (numtiles == 1 ? " staf" : " stafi");
         }
         else
         if (word == "RSGN")
            /* Resigned from game */
            word = "Gaf leikinn";
         else
         if (word == "OVER") {
            /* Game over */
            word = "Leik lokið";
            wrdclass = "gameover"; /* !!! TODO: use a different class from leftmove/rightmove below */
         }
         else
            /* The rack leave at the end of the game */
            wrdclass = "wordmove";
      }
      else
         coord = "(" + coord + ")";
      if (wrdclass == "gameover") {
         str = '<div class="gameover">' + word + '</div>';
      }
      else
      if (player == 0) {
         str = '<div class="leftmove"><span class="score">' + score + '</span>' +
            '<span class="' + wrdclass + '"><i>' + word + '</i> ' + coord + '</span></div>';
      }
      else {
         str = '<div class="rightmove"><span class="' + wrdclass + '">' + coord + ' <i>' + word + '</i></span>' +
            '<span class="score">' + score + '</span></div>';
      }
      movelist = $("div.movelist");
      movelist.append(str);
      if (wrdclass != "gameover")
         if (player == humanPlayer())
            $("div.movelist").children().last().addClass("humancolor");
         else
            $("div.movelist").children().last().addClass("autoplayercolor");
      /* Manage the scrolling of the move list */
      lastchild = $("div.movelist:last-child");
      firstchild = $("div.movelist").children().eq(0); /* :first-child doesn't work?! */
      topoffset = lastchild.position().top -
         firstchild.position().top +
         lastchild.height();
      height = movelist.height()
      if (topoffset >= height)
         movelist.scrollTop(topoffset - height)
   }

   var elementDragged = null;
   var showingDialog = false;

   function handleDragstart(e) {
      /* The dragstart target is the DIV inside a TD */
      e.dataTransfer.clearData();
      e.dataTransfer.setData('text/html', ""); /* We don't use this */
      e.dataTransfer.effectAllowed = 'move';
      /* e.dataTransfer.setDragImage(e.target.innerHTML); */
      elementDragged = e.target;
      elementDragged.style.opacity = "0.6"
   }

   function handleDragend(e) {
      if (elementDragged != null)
         elementDragged.style.opacity = "1.0";
      elementDragged = null;
   }

   function initDraggable(elem) {
      /* The DIVs inside the board TDs are draggable */
      elem.addEventListener('dragstart', handleDragstart);
      elem.addEventListener('dragend', handleDragend);
   }

   function initRackDraggable() {
      for (i = 1; i <= 7; i++) {
         rackTileId = "R" + i.toString();
         rackTile = document.getElementById(rackTileId);
         if (rackTile && rackTile.firstChild)
            initDraggable(rackTile.firstChild);
      }
   }

   function handleDragover(e) {
      if (e.preventDefault)
         e.preventDefault();
      if (e.target.firstChild)
        /* There is already a tile in the square: drop will have no effect */
        e.dataTransfer.dropEffect = 'none';
      else
        e.dataTransfer.dropEffect = 'move';
      return false;
   }

   function handleDragenter(e) {
      if (e.target.firstChild == null)
        /* Empty square, can drop here: add yellow outline highlight to square*/
        this.classList.add("over");
   }

   function handleDragleave(e) {
      /* Can drop here: remove outline highlight from square */
      this.classList.remove("over");
   }

   function promptForBlank() {
      var defq = "Hvaða staf táknar auða flísin?";
      var err = "\nSláðu inn einn staf í íslenska stafrófinu."
      var q = defq;
      while(true) {
         letter = prompt(q);
         if (letter == null)
            /* Pressed Esc or terminated */
            return null;
         if (letter.length != 1) {
            q = defq + err;
            continue;
         }
         letter = letter.toLowerCase();
         if ("aábdðeéfghiíjklmoóprstuúvxyýþæö".indexOf(letter) == -1) {
            q = defq + err;
            continue;
         }
         return letter;
      }
   }

   function handleDrop(e) {
      if (e.preventDefault)
         e.preventDefault();
      if (e.stopPropagation)
         e.stopPropagation();
      /* Save the elementDragged value as it will be set to null in handleDragend() */
      var eld = elementDragged;
      e.target.classList.remove("over");
      if (eld != null)
         eld.style.opacity = "1.0";
      if (e.target.firstChild == null && eld != null &&
         eld != e.target.firstChild) {
         /* Looks like a legitimate drop */
         var ok = true;
         parentid = eld.parentNode.id;
         if (parentid.charAt(0) == 'R') {
            /* Dropping from the rack */
            var t = $(eld).data("tile");
            if (t == '?') {
               /* Dropping a blank tile: we need to ask for its meaning */
               e.target.classList.add("over");
               eld.style.opacity = "0.6";
               letter = promptForBlank();
               eld.style.opacity = "1.0";
               e.target.classList.remove("over");
               if (letter == null)
                  ok = false;
               else {
                  $(eld).data("letter", letter);
                  $(eld).addClass("blanktile");
                  eld.childNodes[0].nodeValue = letter;
               }
            }
         }
         if (ok) {
            /* Complete the drop */
            eld.parentNode.removeChild(eld);
            e.target.appendChild(eld);
         }
         elementDragged = null;
         updateSubmitMove();
      }
      return false;
   }

   function initDropTarget(elem) {
      if (elem) {
         elem.addEventListener('dragover', handleDragover);
         elem.addEventListener('dragenter', handleDragenter);
         elem.addEventListener('dragleave', handleDragleave);
         elem.addEventListener('drop', handleDrop);
      }
   }

   function removeDropTarget(elem) {
      if (elem) {
         elem.removeEventListener('dragover', handleDragover);
         elem.removeEventListener('dragenter', handleDragenter);
         elem.removeEventListener('dragleave', handleDragleave);
         elem.removeEventListener('drop', handleDrop);
      }
   }

   function initDropTargets() {
      for (x = 1; x <= 15; x++)
         for (y = 1; y <= 15; y++) {
            coord = "ABCDEFGHIJKLMNO".charAt(y - 1) + x.toString();
            sq = document.getElementById(coord);
            if (sq)
               initDropTarget(sq);
         }
      /* Make the rack a drop target as well */
      for (x = 1; x <= 7; x++) {
        coord = "R" + x.toString();
        sq = document.getElementById(coord);
        if (sq)
           initDropTarget(sq);
      }
   }

   function updateSubmitMove() {
      $("div.submitmove").toggleClass("disabled", (findCovers().length == 0 || showingDialog));
   }

   function submitover() {
      if (!$("div.submitmove").hasClass("disabled") && !showingDialog)
         $("div.submitmove").toggleClass("over", true);
   }

   function submitout() {
      $("div.submitmove").toggleClass("over", false);
   }

   function findCovers() {
      var moves = [];
      $("div.tile").each(function() {
         var sq = $(this).parent().attr("id");
         var t = $(this).data("tile");
         if (t != null && t != undefined && sq.charAt(0) != "R") {
            if (t == '?')
               /* Blank tile: add its meaning */
               t += $(this).data("letter");
            moves.push(sq + "=" + t);
         }
      });
      return moves;      
   }

   var GAME_OVER = 13;

   function updateState(json) {
      /* Work through the returned JSON object to update the
         board, the rack, the scores and the move history */
      if (json.result == 0 || json.result == GAME_OVER) {
         /* Successful move */
         /* Reinitialize the rack */
         var i = 0;
         if (json.result == 0)
            for (i = 0; i < json.rack.length; i++)
               placeTile("R" + (i + 1).toString(), json.rack[i][0], json.rack[i][0], json.rack[i][1]);
         for (; i < 7; i++)
            placeTile("R" + (i + 1).toString(), "", "", 0);
         if (json.result == 0)
            initRackDraggable();
         /* Glue the laid-down tiles to the board */
         $("div.tile").each(function() {
            var sq = $(this).parent().attr("id");
            var t = $(this).data("tile");
            var score = $(this).data("score");
            if (t != null && t !== undefined && sq.charAt(0) != "R") {
               var letter = t;
               if (letter == '?') {
                  /* Blank tile: get its meaning */
                  letter = $(this).data("letter");
                  if (letter == null || letter == undefined)
                     letter = t;
               }
               placeTile(sq, t, letter, score);
            }
         });
         /* Add the new tiles laid down in response */
         if (json.lastmove !== undefined)
            for (i = 0; i < json.lastmove.length; i++) {
               sq = json.lastmove[i][0];
               placeTile(sq, json.lastmove[i][1], json.lastmove[i][2], json.lastmove[i][3]);
               $("#"+sq).children().eq(0).addClass("freshtile");
            }
         /* Update the scores */
         $(".scoreleft").text(json.scores[0]);
         $(".scoreright").text(json.scores[1]);
         /* Update the move list */
         if (json.newmoves !== undefined) {
            for (i = 0; i < json.newmoves.length; i++) {
               player = json.newmoves[i][0];
               coord = json.newmoves[i][1][0];
               word = json.newmoves[i][1][1];
               score = json.newmoves[i][1][2];
               appendMove(player, coord, word, score);
            }
         }
         /* Refresh the submit button */
         updateSubmitMove();
         if (json.result == GAME_OVER) {
            /* Game over: disable Pass, Exchange and Resign buttons */
            $("div.submitpass").toggleClass("disabled", true);
            $("div.submitresign").toggleClass("disabled", true);
            $("div.submitexchange").toggleClass("disabled", true);
         }
      }
      else {
         /* Genuine error: display in error bar */
         $("div.error").css("visibility", "visible").find("p").css("display", "none");
         $("div.error").find("#err_" + json.result.toString()).css("display", "inline");
      }
   }

   function submitPass() {
      if (!$("div.submitpass").hasClass("disabled"))
         submitMove('pass');
   }

   function submitExchange() {
      if (!$("div.submitexchange").hasClass("disabled"))
         submitMove('exch');
   }

   function confirmResign(yes) {
      $("div.resign").css("visibility", "hidden");
      showingDialog = false;
      $("div.submitpass").toggleClass("disabled", false);
      $("div.submitresign").toggleClass("disabled", false);
      $("div.submitexchange").toggleClass("disabled", false);
      updateSubmitMove();
      if (yes)
         submitMove('rsgn');
   }

   function submitResign() {
      if (!$("div.submitresign").hasClass("disabled")) {
         /* Show the yes/no panel */
         $("div.resign").css("visibility", "visible");
         showingDialog = true;
         /* Disable all other actions while panel is shown */
         $("div.submitpass").toggleClass("disabled", true);
         $("div.submitresign").toggleClass("disabled", true);
         $("div.submitexchange").toggleClass("disabled", true);
         $("div.submitmove").toggleClass("disabled", true);
      }
   }

   var submitTemp = "";

   function submitMove(movetype) {
      var moves = [];
      if (movetype == null || movetype == 'move') {
         if ($("div.submitmove").hasClass("disabled"))
            return;
         moves = findCovers();
      }
      else
      if (movetype == 'pass') {
         moves.push("pass");
      }
      else
      if (movetype == 'exch') {
         moves.push("exch=" + exchangeTiles());
      }
      else
      if (movetype == 'rsgn') {
         moves.push("rsgn");
      }
      if (moves.length == 0)
         return;
      /* Erase previous error message, if any */
      $("div.error").css("visibility", "hidden");
      /* Freshly laid tiles are no longer fresh */
      $("div.freshtile").removeClass("freshtile");
      /* Remove highlight from button */
      submitout();
      submitTemp = $("div.submitmove").html();
      $("div.submitmove").html("<img src='static/ajax-loader.gif' border=0/>");
      /* Talk to the game server using jQuery/Ajax */
      $.ajax({
         // the URL for the request
         url: "/submitmove",

         // the data to send
         data: {
            moves: moves
         },

         // whether this is a POST or GET request
         type: "POST",

         // the type of data we expect back
         dataType : "json",

         cache: false,

         // code to run if the request succeeds;
         // the response is passed to the function
         success: updateState,

         // code to run if the request fails; the raw request and
         // status codes are passed to the function
         error: function(xhr, status, errorThrown) {
            alert("Villa í netsamskiptum");
            console.log("Error: " + errorThrown);
            console.log("Status: " + status);
            console.dir(xhr);
         },

         // code to run regardless of success or failure
         complete: function( xhr, status ) {
            $("div.submitmove").html(submitTemp);
         }
      });
   }

   function initSkrafl(jQuery) {
      placeTiles();
      initRackDraggable();
      initDropTargets();
      initMoveList();
      if (humanPlayer() == 0) {
         $("h3.playerleft").addClass("humancolor");
         $("h3.playerright").addClass("autoplayercolor");
      }
      else {
         $("h3.playerright").addClass("humancolor");
         $("h3.playerleft").addClass("autoplayercolor");
      }
   }


