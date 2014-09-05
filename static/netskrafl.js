
/*
   Netskrafl.js
   Author: Vilhjalmur Thorsteinsson, 2014
*/

   function placeTile(sq, t, score) {
      if (sq.charAt(0) == "R")
         attr = "class='tile racktile' draggable='true'";
      else
         attr = "class='tile'";
      $("#"+sq).html("<div " + attr + ">" + t +
         "<div class='letterscore'>" + score + "</div></div>");
      if (sq.charAt(0) == "R")
         $("#"+sq).children().eq(0).data("tile", t);
   }

   var elementDragged = null;

   function handleDragstart(e) {
      e.dataTransfer.clearData();
      e.dataTransfer.setData('text/html', ""); /* We don't use this */
      e.dataTransfer.effectAllowed = 'move';
      /* e.dataTransfer.setDragImage(this); */
      elementDragged = e.target;
   }

   function handleDragend(e) {
      /* p = e.target.parentNode;
      p.removeChild(e.target); */
      /* initDropTarget(elementDragged); */
      /* Make the empty rack tile a drop target */
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
      /* Make the rack a drop targets as well */
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

   function updateState(json) {
      /* Work through the returned JSON object to update the
         board, the rack, the scores and the move history */
      $( "<h1/>" ).text( json.title ).appendTo( "body" );
      $( "<div class=\"content\"/>").html( json.html ).appendTo( "body" );
   }

   function submitMove() {
      var moves = findCovers();
      if (moves.length == 0)
         return;
      /* Talk to the game server using jQuery/Ajax */
      $.ajax({
         // the URL for the request
         url: "/submitmove",

         // the data to send (will be converted to a query string)
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
           alert( "The request is complete!" );
         }
      });
   }

   function initSkrafl(jQuery) {
      placeTiles();
      initRackDraggable();
      initDropTargets();
   }


