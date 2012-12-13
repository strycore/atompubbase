$(document).ready(function() {
  $("span.Log").before("<button class='show'>Show</button>");
  $("button.show").click(function() {
    if ($(this).text() == "Show") {
      $(this).siblings("span.Log").show("slow").end().text("Hide");
    } else {
      $(this).siblings("span.Log").hide("slow").end().text("Show");
 
    }
  });
  prettyPrint();
});

