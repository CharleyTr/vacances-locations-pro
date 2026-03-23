Uploadez pages/messages.py

exec(code, module.__dict__) # noqa: S102DeltaGeneratorDeltaGenerator(_provided_cursor=LockedCursor(_transient_elements=SparseList({}), _index=5, _parent_path=(), _props={'delta_type': 'alert', 'add_rows_metadata': None}), _parent=DeltaGenerator(), _form_data=FormData(form_id=''))
Creator of Delta protobuf messages.

Parameters
----------
root_container: BlockPath_pb2.BlockPath.ContainerValue or None
  The root container for this DeltaGenerator. If None, this is a null
  DeltaGenerator which doesn't print to the app at all (useful for
  testing).

cursor: cursor.Cursor or None
  This is either:
  - None: if this is the running DeltaGenerator for a top-level
    container (MAIN or SIDEBAR)
  - RunningCursor: if this is the running DeltaGenerator for a
    non-top-level container (created with dg.container())
  - LockedCursor: if this is a locked DeltaGenerator returned by some
    other DeltaGenerator method. E.g. the dg returned in dg =
    st.text("foo").

parent: DeltaGenerator
  To support the `with dg` notation, DGs are arranged as a tree. Each DG
  remembers its own parent, and the root of the tree is the main DG.

block_type: None or "vertical" or "horizontal" or "column" or "expandable"
  If this is a block DG, we track its type to prevent nested columns/expanders
dgproperty	Get our DeltaGenerator.
idproperty	Property attribute.
add_rowsmethod	Concatenate a dataframe to the bottom of the current one.
altair_chartmethod	Display a chart using the Vega-Altair library.
area_chartmethod	Display an area chart.
audiomethod	Display an audio player.
audio_inputmethod	Display a widget that returns an audio recording from the user's microphone.
badgemethod	Display a colored badge with an icon and label.
balloonsmethod	Draw celebratory balloons.
bar_chartmethod	Display a bar chart.
bokeh_chartmethod	Display an interactive Bokeh chart.
buttonmethod	Display a button widget.
camera_inputmethod	Display a widget that returns pictures from the user's webcam.
captionmethod	Display text in small font.
chat_inputmethod	Display a chat input widget.
chat_messagemethod	Insert a chat message container.
checkboxmethod	Display a checkbox widget.
codemethod	Display a code block with optional syntax highlighting.
color_pickermethod	Display a color picker widget.
columnsmethod	Insert containers laid out as side-by-side columns.
containermethod	Insert a multi-element container.
data_editormethod	Display a data editor widget.
dataframemethod	Display a dataframe as an interactive table.
date_inputmethod	Display a date input widget.
datetime_inputmethod	Display a date and time input widget.
dividermethod	Display a horizontal rule.
download_buttonmethod	Display a download button widget.
emptymethod	Insert a single-element container.
errormethod	Display error message.
exceptionmethod	Display an exception.
expandermethod	Insert a multi-element container that can be expanded/collapsed.
feedbackmethod	Display a feedback widget.
file_uploadermethod	Display a file uploader widget.
formmethod	Create a form that batches elements together with a "Submit" button.
form_submit_buttonmethod	Display a form submit button.
graphviz_chartmethod	Display a graph using the dagre-d3 library.
headermethod	Display text in header formatting.
helpmethod	Display help and other information for a given object.
htmlmethod	Insert HTML into your app.
imagemethod	Display an image or list of images.
infomethod	Display an informational message.
jsonmethod	Display an object or string as a pretty-printed, interactive JSON string.
latexmethod	Display mathematical expressions formatted as LaTeX.
line_chartmethod	Display a line chart.
link_buttonmethod	Display a link button element.
mapmethod	Display a map with a scatterplot overlaid onto it.
markdownmethod	Display string formatted as Markdown.
metricmethod	Display a metric in big bold font, with an optional indicator of how the metric changed.
multiselectmethod	Display a multiselect widget.
number_inputmethod	Display a numeric input widget.
page_linkmethod	Display a link to another page in a multipage app or to an external page.
pdfmethod	Display a PDF viewer.
pillsmethod	Display a pills widget.
plotly_chartmethod	Display an interactive Plotly chart.
popovermethod	Insert a popover container.
progressmethod	Display a progress bar.
pydeck_chartmethod	Draw a chart using the PyDeck library.
pyplotmethod	Display a matplotlib.pyplot figure.
radiomethod	Display a radio button widget.
scatter_chartmethod	Display a scatterplot chart.
segmented_controlmethod	Display a segmented control widget.
select_slidermethod	Display a slider widget to select items from a list.
selectboxmethod	Display a select widget.
slidermethod	Display a slider widget.
snowmethod	Draw celebratory snowfall.
spacemethod	Add vertical or horizontal space.
spinnermethod	Display a loading spinner while executing a block of code.
statusmethod	Insert a status container to display output from long-running tasks.
subheadermethod	Display text in subheader formatting.
successmethod	Display a success message.
tablemethod	Display a static table.
tabsmethod	Insert containers separated into tabs.
textmethod	Write text without Markdown or HTML parsing.
text_areamethod	Display a multi-line text input widget.
text_inputmethod	Display a single-line text input widget.
time_inputmethod	Display a time input widget.
titlemethod	Display text in title formatting.
toastmethod	Display a short message, known as a notification "toast".
togglemethod	Display a toggle widget.
vega_lite_chartmethod	Display a chart using the Vega-Lite library.
videomethod	Display a video player.
warningmethod	Display warning message.
writemethod	Displays arguments in the app.
write_streammethod	Stream a generator, iterable, or stream-like sequence to the app.
