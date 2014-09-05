
/*
   Netskrafl.js
   Author: Vilhjalmur Thorsteinsson, 2014
*/

   function placeTile(sq, tile, letter, score) {
      if (tile.length == 0) {
         /* Erasing tile */
         $("#"+sq).html("");
         return;
      }
      if (sq.charAt(0) == "R") {
         attr = "class='tile racktile' draggable='true'";
         letter = (tile == "?") ? "&nbsp;" : tile;
      }
      else
         attr = "class='tile'";
      $("#"+sq).html("<div " + attr + ">" + letter +
         "<div class='letterscore'>" + score + "</div></div>");
      if (sq.charAt(0) == "R") {
         $("#"+sq).children().eq(0).data("tile", tile);
         $("#"+sq).children().eq(0).data("score", score);
      }
      else
      if (tile == '?') {
         $("#"+sq).children().eq(0).addClass("blanktile");
      }
   }

   var elementDragged = null;

   function handleDragstart(e) {
      e.dataTransfer.clearData();
      e.dataTransfer.setData('text/html', ""); /* We don't use this */
      e.dataTransfer.effectAllowed = 'move';
      /* e.dataTransfer.setDragImage(e.target.innerHTML); */
      elementDragged = e.target;
      elementDragged.style.opacity = "0.6"
   }

   function handleDragend(e) {
      /* p = e.target.parentNode;
      p.removeChild(e.target); */
      /* initDropTarget(elementDragged); */
      /* Make the empty rack tile a drop target */
      if (elementDragged != null)
         elementDragged.style.opacity = "1.0";
      elementDragged = null;
   }

   function initDraggable(elem) {
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
        /* Can drop here: add yellow outline highlight to square*/
        this.classList.add("over");
   }

   function handleDragleave(e) {
      /* Can drop here: remove outline highlight from square */
      this.classList.remove("over");
   }

   function handleDrop(e) {
      if (e.preventDefault)
         e.preventDefault();
      if (e.stopPropagation)
         e.stopPropagation();
      e.target.classList.remove("over");
      if (e.target.firstChild == null && elementDragged != null &&
         elementDragged != e.target.firstChild) {
         elementDragged.style.opacity = "1.0";
         elementDragged.parentNode.removeChild(elementDragged);
         e.target.appendChild(elementDragged);
         elementDragged = null;
         updateSubmitMove();
      }
      /* On a successful drop, remove the dragover/enter/leave/drop handlers from
         the containing TD, and add new dragstart handlers to
         the new contained DIV. Also add dragover to the empty tile in the rack. */
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
      $("div.submitmove").toggleClass("disabled", (findCovers().length == 0));
   }

   function submitover() {
      if (!$("div.submitmove").hasClass("disabled"))
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
         if (t != null && t != undefined && sq.charAt(0) != "R")
            moves.push(sq + "=" + t);
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
            if (t != null && t !== undefined && sq.charAt(0) != "R")
               placeTile(sq, t, t, score);
         });
         /* Add the new tiles laid down in response */
         if (json.lastmove !== undefined)
            for (i = 0; i < json.lastmove.length; i++) {
               /* !!! Maybe do something fancy here to identify the tiles */
               sq = json.lastmove[i][0];
               placeTile(sq, json.lastmove[i][1], json.lastmove[i][2], json.lastmove[i][3]);
               $("#"+sq).children().eq(0).addClass("freshtile");
            }
         /* Update the scores */
         $(".scoreleft").text(json.scores[0]);
         $(".scoreright").text(json.scores[1]);
         updateSubmitMove();
      }
      else {
         /* Genuine error: display in error bar */
         $("div.error").css("visibility", "visible").find("p").css("display", "none");
         $("div.error").find("#err_" + json.result.toString()).css("display", "inline");
      }
   }

   function submitMove() {
      var moves = findCovers();
      if (moves.length == 0)
         return;
      /* Erase previous error message, if any */
      $("div.error").css("visibility", "hidden");
      /* Freshly laid tiles are no longer fresh */
      $("div.freshtile").removeClass("freshtile");
      /* Remove highlight from button */
      submitout();
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
         error: function( xhr, status, errorThrown ) {
            alert( "Sorry, there was a problem!" );
            console.log( "Error: " + errorThrown );
            console.log( "Status: " + status );
            console.dir( xhr );
         },

         // code to run regardless of success or failure
         complete: function( xhr, status ) {
            /* Don't need this */
         }
      });
   }

   function initSkrafl(jQuery) {
      placeTiles();
      initRackDraggable();
      initDropTargets();
   }


