/**
RhodeCode JS Files
**/

if (typeof console == "undefined" || typeof console.log == "undefined"){
    console = { log: function() {} }
}

/**
 * INJECT .format function into String
 * Usage: "My name is {0} {1}".format("Johny","Bravo")
 * Return "My name is Johny Bravo"
 * Inspired by https://gist.github.com/1049426
 */
String.prototype.format = function() {
    function format() {
        var str = this;
        var len = arguments.length+1;
        var safe = undefined;
        var arg = undefined;

        // For each {0} {1} {n...} replace with the argument in that position.  If
        // the argument is an object or an array it will be stringified to JSON.
        for (var i=0; i < len; arg = arguments[i++]) {
            safe = typeof arg === 'object' ? JSON.stringify(arg) : arg;
            str = str.replace(RegExp('\\{'+(i-1)+'\\}', 'g'), safe);
        }
        return str;
    }

    // Save a reference of what may already exist under the property native.
    // Allows for doing something like: if("".format.native) { /* use native */ }
    format.native = String.prototype.format;

    // Replace the prototype property
    return format;

}();

String.prototype.strip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp('^'+char+'+|'+char+'+$','g'), '');
}

String.prototype.lstrip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp('^'+char+'+'),'');
}

String.prototype.rstrip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp(''+char+'+$'),'');
}


if(!Array.prototype.indexOf) {
    Array.prototype.indexOf = function(needle) {
        for(var i = 0; i < this.length; i++) {
            if(this[i] === needle) {
                return i;
            }
        }
        return -1;
    };
}

/* https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter#Compatibility
   under MIT license / public domain, see
   https://developer.mozilla.org/en-US/docs/MDN/About#Copyrights_and_licenses */
if (!Array.prototype.filter)
{
    Array.prototype.filter = function(fun /*, thisArg */)
    {
        "use strict";

        if (this === void 0 || this === null)
            throw new TypeError();

        var t = Object(this);
        var len = t.length >>> 0;
        if (typeof fun !== "function")
            throw new TypeError();

        var res = [];
        var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
        for (var i = 0; i < len; i++)
        {
            if (i in t)
            {
                var val = t[i];

                // NOTE: Technically this should Object.defineProperty at
                //       the next index, as push can be affected by
                //       properties on Object.prototype and Array.prototype.
                //       But that method's new, and collisions should be
                //       rare, so use the more-compatible alternative.
                if (fun.call(thisArg, val, i, t))
                    res.push(val);
            }
        }

        return res;
    };
}

/**
 * A customized version of PyRoutes.JS from https://pypi.python.org/pypi/pyroutes.js/
 * which is copyright Stephane Klein and was made available under the BSD License.
 *
 * Usage pyroutes.url('mark_error_fixed',{"error_id":error_id}) // /mark_error_fixed/<error_id>
 */
var pyroutes = (function() {
    // access global map defined in special file pyroutes
    var matchlist = PROUTES_MAP;
    var sprintf = (function() {
        function get_type(variable) {
            return Object.prototype.toString.call(variable).slice(8, -1).toLowerCase();
        }
        function str_repeat(input, multiplier) {
            for (var output = []; multiplier > 0; output[--multiplier] = input) {/* do nothing */}
            return output.join('');
        }

        var str_format = function() {
            if (!str_format.cache.hasOwnProperty(arguments[0])) {
                str_format.cache[arguments[0]] = str_format.parse(arguments[0]);
            }
            return str_format.format.call(null, str_format.cache[arguments[0]], arguments);
        };

        str_format.format = function(parse_tree, argv) {
            var cursor = 1, tree_length = parse_tree.length, node_type = '', arg, output = [], i, k, match, pad, pad_character, pad_length;
            for (i = 0; i < tree_length; i++) {
                node_type = get_type(parse_tree[i]);
                if (node_type === 'string') {
                    output.push(parse_tree[i]);
                }
                else if (node_type === 'array') {
                    match = parse_tree[i]; // convenience purposes only
                    if (match[2]) { // keyword argument
                        arg = argv[cursor];
                        for (k = 0; k < match[2].length; k++) {
                            if (!arg.hasOwnProperty(match[2][k])) {
                                throw(sprintf('[sprintf] property "%s" does not exist', match[2][k]));
                            }
                            arg = arg[match[2][k]];
                        }
                    }
                    else if (match[1]) { // positional argument (explicit)
                        arg = argv[match[1]];
                    }
                    else { // positional argument (implicit)
                        arg = argv[cursor++];
                    }

                    if (/[^s]/.test(match[8]) && (get_type(arg) != 'number')) {
                        throw(sprintf('[sprintf] expecting number but found %s', get_type(arg)));
                    }
                    switch (match[8]) {
                        case 'b': arg = arg.toString(2); break;
                        case 'c': arg = String.fromCharCode(arg); break;
                        case 'd': arg = parseInt(arg, 10); break;
                        case 'e': arg = match[7] ? arg.toExponential(match[7]) : arg.toExponential(); break;
                        case 'f': arg = match[7] ? parseFloat(arg).toFixed(match[7]) : parseFloat(arg); break;
                        case 'o': arg = arg.toString(8); break;
                        case 's': arg = ((arg = String(arg)) && match[7] ? arg.substring(0, match[7]) : arg); break;
                        case 'u': arg = Math.abs(arg); break;
                        case 'x': arg = arg.toString(16); break;
                        case 'X': arg = arg.toString(16).toUpperCase(); break;
                    }
                    arg = (/[def]/.test(match[8]) && match[3] && arg >= 0 ? '+'+ arg : arg);
                    pad_character = match[4] ? match[4] == '0' ? '0' : match[4].charAt(1) : ' ';
                    pad_length = match[6] - String(arg).length;
                    pad = match[6] ? str_repeat(pad_character, pad_length) : '';
                    output.push(match[5] ? arg + pad : pad + arg);
                }
            }
            return output.join('');
        };

        str_format.cache = {};

        str_format.parse = function(fmt) {
            var _fmt = fmt, match = [], parse_tree = [], arg_names = 0;
            while (_fmt) {
                if ((match = /^[^\x25]+/.exec(_fmt)) !== null) {
                    parse_tree.push(match[0]);
                }
                else if ((match = /^\x25{2}/.exec(_fmt)) !== null) {
                    parse_tree.push('%');
                }
                else if ((match = /^\x25(?:([1-9]\d*)\$|\(([^\)]+)\))?(\+)?(0|'[^$])?(-)?(\d+)?(?:\.(\d+))?([b-fosuxX])/.exec(_fmt)) !== null) {
                    if (match[2]) {
                        arg_names |= 1;
                        var field_list = [], replacement_field = match[2], field_match = [];
                        if ((field_match = /^([a-z_][a-z_\d]*)/i.exec(replacement_field)) !== null) {
                            field_list.push(field_match[1]);
                            while ((replacement_field = replacement_field.substring(field_match[0].length)) !== '') {
                                if ((field_match = /^\.([a-z_][a-z_\d]*)/i.exec(replacement_field)) !== null) {
                                    field_list.push(field_match[1]);
                                }
                                else if ((field_match = /^\[(\d+)\]/.exec(replacement_field)) !== null) {
                                    field_list.push(field_match[1]);
                                }
                                else {
                                    throw('[sprintf] huh?');
                                }
                            }
                        }
                        else {
                            throw('[sprintf] huh?');
                        }
                        match[2] = field_list;
                    }
                    else {
                        arg_names |= 2;
                    }
                    if (arg_names === 3) {
                        throw('[sprintf] mixing positional and named placeholders is not (yet) supported');
                    }
                    parse_tree.push(match);
                }
                else {
                    throw('[sprintf] huh?');
                }
                _fmt = _fmt.substring(match[0].length);
            }
            return parse_tree;
        };

        return str_format;
    })();

    var vsprintf = function(fmt, argv) {
        argv.unshift(fmt);
        return sprintf.apply(null, argv);
    };
    return {
        'url': function(route_name, params) {
            var result = route_name;
            if (typeof(params) != 'object'){
                params = {};
            }
            if (matchlist.hasOwnProperty(route_name)) {
                var route = matchlist[route_name];
                // param substitution
                for(var i=0; i < route[1].length; i++) {
                   if (!params.hasOwnProperty(route[1][i]))
                        throw new Error(route[1][i] + ' missing in "' + route_name + '" route generation');
                }
                result = sprintf(route[0], params);

                var ret = [];
                //extra params => GET
                for(param in params){
                    if (route[1].indexOf(param) == -1){
                        ret.push(encodeURIComponent(param) + "=" + encodeURIComponent(params[param]));
                    }
                }
                var _parts = ret.join("&");
                if(_parts){
                    result = result +'?'+ _parts
                }
            }

            return result;
        },
        'register': function(route_name, route_tmpl, req_params) {
            if (typeof(req_params) != 'object') {
                req_params = [];
            }
            //fix escape
            route_tmpl = unescape(route_tmpl);
            keys = [];
            for (o in req_params){
                keys.push(req_params[o])
            }
            matchlist[route_name] = [
                route_tmpl,
                keys
            ]
        },
        '_routes': function(){
            return matchlist;
        }
    }
})();


/**
 * GLOBAL YUI Shortcuts
 */
var YUC = YAHOO.util.Connect;
var YUD = YAHOO.util.Dom;
var YUE = YAHOO.util.Event;
var YUQ = YAHOO.util.Selector.query;

/* Invoke all functions in callbacks */
var _run_callbacks = function(callbacks){
    if (callbacks !== undefined){
        var _l = callbacks.length;
        for (var i=0;i<_l;i++){
            var func = callbacks[i];
            if(typeof(func)=='function'){
                try{
                    func();
                }catch (err){};
            }
        }
    }
}

/**
 * turns objects into GET query string
 */
var _toQueryString = function(o) {
    if(typeof o !== 'object') {
        return false;
    }
    var _p, _qs = [];
    for(_p in o) {
        _qs.push(encodeURIComponent(_p) + '=' + encodeURIComponent(o[_p]));
    }
    return _qs.join('&');
};

/**
 * Partial Ajax Implementation
 *
 * @param url: defines url to make partial request
 * @param container: defines id of container to input partial result
 * @param s_call: success callback function that takes o as arg
 *  o.tId
 *  o.status
 *  o.statusText
 *  o.getResponseHeader[ ]
 *  o.getAllResponseHeaders
 *  o.responseText
 *  o.responseXML
 *  o.argument
 * @param f_call: failure callback
 * @param args arguments
 */
function ypjax(url,container,s_call,f_call,args){
    var method='GET';
    if(args===undefined){
        args=null;
    }
    $container = $('#' + container);

    // Set special header for partial ajax == HTTP_X_PARTIAL_XHR
    YUC.initHeader('X-PARTIAL-XHR',true);

    // wrapper of passed callback
    var s_wrapper = (function(o){
        return function(o){
            $container.html(o.responseText);
            $container.css('opacity','1.0');
            //execute the given original callback
            if (s_call !== undefined){
                s_call(o);
            }
        }
    })()
    $container.css('opacity','0.3');
    YUC.asyncRequest(method,url,{
        success:s_wrapper,
        failure:function(o){
            console.log('ypjax failure: '+o);
            $container.html('<span class="error_red">ERROR: {0}</span>'.format(o.status));
            $container.css('opacity','1.0');
        },
        cache:false
    },args);

};

var ajaxGET = function(url,success) {
    // Set special header for ajax == HTTP_X_PARTIAL_XHR
    YUC.initHeader('X-PARTIAL-XHR',true);

    var sUrl = url;
    var callback = {
        success: success,
        failure: function (o) {
            if (o.status != 0) {
                alert("error: " + o.statusText);
            };
        },
    };

    var request = YAHOO.util.Connect.asyncRequest('GET', sUrl, callback);
    return request;
};

var ajaxPOST = function(url,postData,success) {
    // Set special header for ajax == HTTP_X_PARTIAL_XHR
    YUC.initHeader('X-PARTIAL-XHR',true);

    var sUrl = url;
    var callback = {
        success: success,
        failure: function (o) {
            alert("error");
        },
    };
    var postData = _toQueryString(postData);
    var request = YAHOO.util.Connect.asyncRequest('POST', sUrl, callback, postData);
    return request;
};


/**
 * activate .show_more links
 * the .show_more must have an id that is the the id of an element to hide prefixed with _
 * the parentnode will be displayed
 */
var show_more_event = function(){
    $('.show_more').click(function(e){
        var el = e.currentTarget;
        $('#' + el.id.substring(1)).hide();
        $(el.parentNode).show();
    });
};

/**
 * activate .lazy-cs mouseover for showing changeset tooltip
 */
var show_changeset_tooltip = function(){
    $('.lazy-cs').mouseover(function(e){
        var $target = $(e.currentTarget);
        var rid = $target.attr('raw_id');
        var repo_name = $target.attr('repo_name');
        if(rid && !$target.hasClass('tooltip')){
            _show_tooltip(e, _TM['loading ...']);
            var url = pyroutes.url('changeset_info', {"repo_name": repo_name, "revision": rid});
            ajaxGET(url, function(o){
                    var json = JSON.parse(o.responseText);
                    $target.addClass('tooltip')
                    _show_tooltip(e, json['message']);
                    _activate_tooltip($target);
                });
        }
    });
};

var _onSuccessFollow = function(target){
    var $target = $(target);
    var $f_cnt = $('#current_followers_count');
    if($target.hasClass('follow')){
        $target.attr('class', 'following');
        $target.attr('title', _TM['Stop following this repository']);
        if($f_cnt.html()){
            var cnt = Number($f_cnt.html())+1;
            $f_cnt.html(cnt);
        }
    }
    else{
        $target.attr('class', 'follow');
        $target.attr('title', _TM['Start following this repository']);
        if($f_cnt.html()){
            var cnt = Number($f_cnt.html())-1;
            $f_cnt.html(cnt);
        }
    }
}

var toggleFollowingRepo = function(target, follows_repo_id, token, user_id){
    args = 'follows_repo_id='+follows_repo_id;
    args+= '&amp;auth_token='+token;
    if(user_id != undefined){
        args+="&amp;user_id="+user_id;
    }
    $.post(TOGGLE_FOLLOW_URL, args, function(data){
            _onSuccessFollow(target);
        });
    return false;
};

var showRepoSize = function(target, repo_name, token){
    var args= 'auth_token='+token;

    if(!$("#" + target).hasClass('loaded')){
        $("#" + target).html(_TM['Loading ...']);
        var url = pyroutes.url('repo_size', {"repo_name":repo_name});
        $.post(url, args, function(data) {
            $("#" + target).html(data);
            $("#" + target).addClass('loaded');
        });
    }
    return false;
};

/**
 * tooltips
 */

var tooltip_activate = function(){
    $(document).ready(_init_tooltip);
};

var _activate_tooltip = function($tt){
    $tt.mouseover(_show_tooltip);
    $tt.mousemove(_move_tooltip);
    $tt.mouseout(_close_tooltip);
};

var _init_tooltip = function(){
    var $tipBox = $('#tip-box');
    if(!$tipBox.length){
        $tipBox = $('<div id="tip-box"></div>')
        $(document.body).append($tipBox);
    }

    $tipBox.hide();
    $tipBox.css('position', 'absolute');
    $tipBox.css('max-width', '600px');

    _activate_tooltip($('.tooltip'));
};

var _show_tooltip = function(e, tipText){
    e.stopImmediatePropagation();
    var el = e.currentTarget;
    if(tipText){
        // just use it
    } else if(el.tagName.toLowerCase() === 'img'){
        tipText = el.alt ? el.alt : '';
    } else {
        tipText = el.title ? el.title : '';
    }

    if(tipText !== ''){
        // save org title
        $(el).attr('tt_title', tipText);
        // reset title to not show org tooltips
        $(el).attr('title', '');

        var $tipBox = $('#tip-box');
        $tipBox.html(tipText);
        $tipBox.css('display', 'block');
    }
};

var _move_tooltip = function(e){
    e.stopImmediatePropagation();
    var $tipBox = $('#tip-box');
    $tipBox.css('top', (e.pageY + 15) + 'px');
    $tipBox.css('left', (e.pageX + 15) + 'px');
};

var _close_tooltip = function(e){
    e.stopImmediatePropagation();
    var $tipBox = $('#tip-box');
    $tipBox.hide();
    var el = e.currentTarget;
    $(el).attr('title', $(el).attr('tt_title'));
};

/**
 * Quick filter widget
 *
 * @param target: filter input target
 * @param nodes: list of nodes in html we want to filter.
 * @param display_element function that takes current node from nodes and
 *    does hide or show based on the node
 */
var q_filter = function(target, nodes, display_element){
    var nodes = nodes;
    var $q_filter_field = $('#' + target);
    var F = YAHOO.namespace(target);

    $q_filter_field.keyup(function(e){
        clearTimeout(F.filterTimeout);
        F.filterTimeout = setTimeout(F.updateFilter, 600);
    });

    F.filterTimeout = null;

    F.updateFilter  = function() {
        // Reset timeout
        F.filterTimeout = null;

        var obsolete = [];

        var req = $q_filter_field.val().toLowerCase();

        var l = nodes.length;
        var i;
        var showing = 0;

        for (i=0; i<l; i++ ){
            var n = nodes[i];
            var target_element = display_element(n)
            if(req && n.innerHTML.toLowerCase().indexOf(req) == -1){
                $(target_element).hide();
            }
            else{
                $(target_element).show();
                showing += 1;
            }
        }

        $('#repo_count').html(showing); /* FIXME: don't hardcode */
    }
};

/* return jQuery expression with a tr with body in 3rd column and class cls and id named after the body */
var _table_tr = function(cls, body){
    // like: <div class="comment" id="comment-8" line="o92"><div class="comment-wrapp">...
    // except new inlines which are different ...
    var comment_id = ($(body).attr('id') || 'comment-new').split('comment-')[1];
    var tr_id = 'comment-tr-{0}'.format(comment_id);
    return $(('<tr id="{0}" class="{1}">'+
                  '<td class="lineno-inline new-inline"></td>'+
                  '<td class="lineno-inline old-inline"></td>'+
                  '<td>{2}</td>'+
                 '</tr>').format(tr_id, cls, body));
};

/** return jQuery expression with new inline form based on template **/
var _createInlineForm = function(parent_tr, f_path, line) {
    var $tmpl = $('#comment-inline-form-template').html().format(f_path, line);
    var $form = _table_tr('comment-form-inline', $tmpl)

    // create event for hide button
    $form.find('.hide-inline-form').click(function(e) {
        var newtr = e.currentTarget.parentNode.parentNode.parentNode.parentNode.parentNode;
        if($(newtr).next().hasClass('inline-comments-button')){
            $(newtr).next().show();
        }
        $(newtr).remove();
        $(parent_tr).removeClass('form-open');
        $(parent_tr).removeClass('hl-comment');
    });

    return $form
};

/**
 * Inject inline comment for an given TR. This tr should always be a .line .
 * The form will be inject after any comments.
 */
var injectInlineForm = function(tr){
    $tr = $(tr);
    if(!$tr.hasClass('line')){
        return
    }
    var submit_url = AJAX_COMMENT_URL;
    var $td = $tr.find('.code');
    if($tr.hasClass('form-open') || $tr.hasClass('context') || $td.hasClass('no-comment')){
        return
    }
    $tr.addClass('form-open hl-comment');
    var $node = $tr.parent().parent().parent().find('.full_f_path');
    var f_path = $node.attr('path');
    var lineno = _getLineNo(tr);
    var $form = _createInlineForm(tr, f_path, lineno, submit_url);

    var $parent = $tr;
    while ($parent.next().hasClass('inline-comments')){
        var $parent = $parent.next();
    }
    $form.insertAfter($parent);
    var $overlay = $form.find('.overlay');
    var $inlineform = $form.find('.inline-form');

    $form.submit(function(e){
        e.preventDefault();

        if(lineno === undefined){
            alert('missing line !');
            return
        }
        if(f_path === undefined){
            alert('missing file path !');
            return
        }

        var text = $('#text_'+lineno).val();
        if(text == ""){
            return
        }

        if ($overlay.hasClass('overlay')){
            $overlay.css('width', $inlineform.offsetWidth + 'px');
            $overlay.css('height', $inlineform.offsetHeight + 'px');
        }
        $overlay.addClass('submitting');

        var success = function(o){
            $tr.removeClass('form-open');
            $form.remove();
            var json_data = JSON.parse(o.responseText);
            _renderInlineComment(json_data);
        };
        var postData = {
                'text': text,
                'f_path': f_path,
                'line': lineno
        };
        ajaxPOST(submit_url, postData, success);
    });

    $('#preview-btn_'+lineno).click(function(e){
        var text = $('#text_'+lineno).val();
        if(!text){
            return
        }
        $('#preview-box_'+lineno).addClass('unloaded');
        $('#preview-box_'+lineno).html(_TM['Loading ...']);
        $('#edit-container_'+lineno).hide();
        $('#preview-container_'+lineno).show();

        var url = pyroutes.url('changeset_comment_preview', {'repo_name': REPO_NAME});
        var post_data = {'text': text};
        ajaxPOST(url, post_data, function(o){
            $('#preview-box_'+lineno).html(o.responseText);
            $('#preview-box_'+lineno).removeClass('unloaded');
        })
    })
    $('#edit-btn_'+lineno).click(function(e){
        $('#edit-container_'+lineno).show();
        $('#preview-container_'+lineno).hide();
    })

    setTimeout(function(){
        // callbacks
        tooltip_activate();
        MentionsAutoComplete('text_'+lineno, 'mentions_container_'+lineno,
                             _USERS_AC_DATA, _GROUPS_AC_DATA);
        $('#text_'+lineno).focus();
    },10)
};

var deleteComment = function(comment_id){
    var url = AJAX_COMMENT_DELETE_URL.replace('__COMMENT_ID__',comment_id);
    var postData = {'_method':'delete'};
    var success = function(o){
        var $deleted = $('#comment-tr-'+comment_id);
        var $prev = $deleted.prev('tr');
        $deleted.remove();
        _placeAddButton($prev);
    }
    ajaxPOST(url,postData,success);
}

var _getLineNo = function(tr) {
    var line;
    var o = $(tr).children()[0].id.split('_');
    var n = $(tr).children()[1].id.split('_');

    if (n.length >= 2) {
        line = n[n.length-1];
    } else if (o.length >= 2) {
        line = o[o.length-1];
    }

    return line
};

var _placeAddButton = function($line_tr){
    var $tr = $line_tr;
    while ($tr.next().hasClass('inline-comments')){
        $tr.find('.add-comment').remove();
        $tr = $tr.next();
    }
    $tr.find('.add-comment').remove();
    var label = TRANSLATION_MAP['Add another comment'];
    var $html_el = $('<div class="add-comment"><span class="ui-btn">{0}</span></div>'.format(label));
    $html_el.click(function(e) {
        injectInlineForm($line_tr);
    });
    $tr.find('.comment').after($html_el);
};

/**
 * Places the inline comment into the changeset block in proper line position
 */
var _placeInline = function(target_id, lineno, html){
    var $td = $("#{0}_{1}".format(target_id, lineno));

    // check if there are comments already !
    var $line_tr = $td.parent(); // the tr
    var $after_tr = $line_tr;
    while ($after_tr.next().hasClass('inline-comments')){
        $after_tr = $after_tr.next();
    }
    // put in the comment at the bottom
    $after_tr.after(_table_tr('inline-comments', html));

    // scan nodes, and attach add button to last one
    _placeAddButton($line_tr);
}

/**
 * make a single inline comment and place it inside
 */
var _renderInlineComment = function(json_data){
    var html =  json_data['rendered_text'];
    var lineno = json_data['line_no'];
    var target_id = json_data['target_id'];
    _placeInline(target_id, lineno, html);
}

/**
 * Iterates over all the inlines, and places them inside proper blocks of data
 */
var renderInlineComments = function(file_comments){
    for (f in file_comments){
        // holding all comments for a FILE
        var box = file_comments[f];

        var target_id = $(box).attr('target_id');
        // actual comments with line numbers
        var comments = box.children;
        for(var i=0; i<comments.length; i++){
            var data = {
                'rendered_text': comments[i].outerHTML,
                'line_no': $(comments[i]).attr('line'),
                'target_id': target_id
            }
            _renderInlineComment(data);
        }
    }
}

/* activate files.html stuff */
var fileBrowserListeners = function(current_url, node_list_url, url_base){
    var current_url_branch = "?branch=__BRANCH__";

    $('#stay_at_branch').on('click',function(e){
        if(e.currentTarget.checked){
            var uri = current_url_branch;
            uri = uri.replace('__BRANCH__',e.currentTarget.value);
            window.location = uri;
        }
        else{
            window.location = current_url;
        }
    })

    var $node_filter = $('#node_filter');

    var filterTimeout = null;
    var nodes = null;

    var initFilter = function(){
        $('#node_filter_box_loading').show();
        $('#search_activate_id').hide();
        $('#add_node_id').hide();
        YUC.initHeader('X-PARTIAL-XHR',true);
        YUC.asyncRequest('GET', node_list_url, {
            success:function(o){
                nodes = JSON.parse(o.responseText).nodes;
                $('#node_filter_box_loading').hide();
                $('#node_filter_box').show();
                $node_filter.focus();
                if($node_filter.hasClass('init')){
                    $node_filter.val('');
                    $node_filter.removeClass('init');
                }
            },
            failure:function(o){
                console.log('failed to load');
            }
        },null);
    }

    var updateFilter = function(e) {
        return function(){
            // Reset timeout
            filterTimeout = null;
            var query = e.currentTarget.value.toLowerCase();
            var match = [];
            var matches = 0;
            var matches_max = 20;
            if (query != ""){
                for(var i=0;i<nodes.length;i++){
                    var pos = nodes[i].name.toLowerCase().indexOf(query)
                    if(query && pos != -1){
                        matches++
                        //show only certain amount to not kill browser
                        if (matches > matches_max){
                            break;
                        }

                        var n = nodes[i].name;
                        var t = nodes[i].type;
                        var n_hl = n.substring(0,pos)
                          +"<b>{0}</b>".format(n.substring(pos,pos+query.length))
                          +n.substring(pos+query.length)
                        var new_url = url_base.replace('__FPATH__',n);
                        match.push('<tr><td><a class="browser-{0}" href="{1}">{2}</a></td><td colspan="5"></td></tr>'.format(t,new_url,n_hl));
                    }
                    if(match.length >= matches_max){
                        match.push('<tr><td>{0}</td><td colspan="5"></td></tr>'.format(_TM['Search truncated']));
                    }
                }
            }
            if(query != ""){
                $('#tbody').hide();
                $('#tbody_filtered').show();

                if (match.length==0){
                  match.push('<tr><td>{0}</td><td colspan="5"></td></tr>'.format(_TM['No matching files']));
                }

                $('#tbody_filtered').html(match.join(""));
            }
            else{
                $('#tbody').show();
                $('#tbody_filtered').hide();
            }
        }
    };

    $('#filter_activate').click(function(){
            initFilter();
        });
    $node_filter.click(function(){
            if($node_filter.hasClass('init')){
                $node_filter.val('');
                $node_filter.removeClass('init');
            }
        });
    $node_filter.keyup(function(e){
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(updateFilter(e),600);
        });
};


var initCodeMirror = function(textarea_id, resetUrl){
    var myCodeMirror = CodeMirror.fromTextArea($('#' + textarea_id)[0], {
            mode: "null",
            lineNumbers: true,
            indentUnit: 4
        });
    $('#reset').click(function(e){
            window.location=resetUrl;
        });

    $('#file_enable').click(function(){
            $('#editor_container').show();
            $('#upload_file_container').hide();
            $('#filename_container').show();
        });

    $('#upload_file_enable').click(function(){
            $('#editor_container').hide();
            $('#upload_file_container').show();
            $('#filename_container').hide();
        });

    return myCodeMirror
};

var setCodeMirrorMode = function(codeMirrorInstance, mode) {
    codeMirrorInstance.setOption("mode", mode);
    CodeMirror.autoLoadMode(codeMirrorInstance, mode);
}


var _getIdentNode = function(n){
    //iterate thrugh nodes until matching interesting node

    if (typeof n == 'undefined'){
        return -1
    }

    if(typeof n.id != "undefined" && n.id.match('L[0-9]+')){
        return n
    }
    else{
        return _getIdentNode(n.parentNode);
    }
};

/* generate links for multi line selects that can be shown by files.html page_highlights.
 * This is a mouseup handler for hlcode from CodeHtmlFormatter and pygmentize */
var getSelectionLink = function(e) {
    //get selection from start/to nodes
    if (typeof window.getSelection != "undefined") {
        s = window.getSelection();

        from = _getIdentNode(s.anchorNode);
        till = _getIdentNode(s.focusNode);

        f_int = parseInt(from.id.replace('L',''));
        t_int = parseInt(till.id.replace('L',''));

        var yoffset = 35;
        var ranges = [parseInt(from.id.replace('L','')), parseInt(till.id.replace('L',''))];
        if (ranges[0] > ranges[1]){
            //highlight from bottom
            yoffset = -yoffset;
            ranges = [ranges[1], ranges[0]];
        }
        var $hl_div = $('div#linktt');
        // if we select more than 2 lines
        if (ranges[0] != ranges[1]){
            if ($hl_div.length) {
                $hl_div.html('');
            } else {
                $hl_div = $('<div id="linktt" class="hl-tip-box">');
                $('body').prepend($hl_div);
            }

            $hl_div.append($('<a>').html(_TM['Selection link']).attr('href', location.href.substring(0, location.href.indexOf('#')) + '#L' + ranges[0] + '-'+ranges[1]));
            xy = $(till).offset();
            $hl_div.css('top', (xy.top + yoffset) + 'px').css('left', xy.left + 'px');
            $hl_div.show();
        }
        else{
            $hl_div.hide();
        }
    }
};

var deleteNotification = function(url, notification_id, callbacks){
    var callback = {
        success:function(o){
            $("#notification_"+notification_id).remove();
            _run_callbacks(callbacks);
        },
        failure:function(o){
            alert("error");
        },
    };
    var postData = '_method=delete';
    var sUrl = url.replace('__NOTIFICATION_ID__',notification_id);
    var request = YAHOO.util.Connect.asyncRequest('POST', sUrl,
                                                  callback, postData);
};

var readNotification = function(url, notification_id, callbacks){
    var callback = {
        success:function(o){
            var $obj = $("#notification_"+notification_id);
            $obj.removeClass('unread');
            $obj.find('.read-notification').remove();
            _run_callbacks(callbacks);
        },
        failure:function(o){
            alert("error");
        },
    };
    var postData = '_method=put';
    var sUrl = url.replace('__NOTIFICATION_ID__',notification_id);
    var request = YAHOO.util.Connect.asyncRequest('POST', sUrl,
                                                  callback, postData);
};

/** MEMBERS AUTOCOMPLETE WIDGET **/

var _MembersAutoComplete = function (divid, cont, users_list, groups_list) {
    var myUsers = users_list;
    var myGroups = groups_list;

    // Define a custom search function for the DataSource of users
    var matchUsers = function (sQuery) {
            // Case insensitive matching
            var query = sQuery.toLowerCase();
            var i = 0;
            var l = myUsers.length;
            var matches = [];

            // Match against each name of each contact
            for (; i < l; i++) {
                contact = myUsers[i];
                if (((contact.fname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.lname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.nname) && ((contact.nname).toLowerCase().indexOf(query) > -1))) {
                    matches[matches.length] = contact;
                }
            }
            return matches;
        };

    // Define a custom search function for the DataSource of userGroups
    var matchGroups = function (sQuery) {
            // Case insensitive matching
            var query = sQuery.toLowerCase();
            var i = 0;
            var l = myGroups.length;
            var matches = [];

            // Match against each name of each contact
            for (; i < l; i++) {
                matched_group = myGroups[i];
                if (matched_group.grname.toLowerCase().indexOf(query) > -1) {
                    matches[matches.length] = matched_group;
                }
            }
            return matches;
        };

    //match all
    var matchAll = function (sQuery) {
            u = matchUsers(sQuery);
            g = matchGroups(sQuery);
            return u.concat(g);
        };

    // DataScheme for members
    var memberDS = new YAHOO.util.FunctionDataSource(matchAll);
    memberDS.responseSchema = {
        fields: ["id", "fname", "lname", "nname", "grname", "grmembers", "gravatar_lnk"]
    };

    // DataScheme for owner
    var ownerDS = new YAHOO.util.FunctionDataSource(matchUsers);
    ownerDS.responseSchema = {
        fields: ["id", "fname", "lname", "nname", "gravatar_lnk"]
    };

    // Instantiate AutoComplete for perms
    var membersAC = new YAHOO.widget.AutoComplete(divid, cont, memberDS);
    membersAC.useShadow = false;
    membersAC.resultTypeList = false;
    membersAC.animVert = false;
    membersAC.animHoriz = false;
    membersAC.animSpeed = 0.1;

    // Instantiate AutoComplete for owner
    var ownerAC = new YAHOO.widget.AutoComplete("user", "owner_container", ownerDS);
    ownerAC.useShadow = false;
    ownerAC.resultTypeList = false;
    ownerAC.animVert = false;
    ownerAC.animHoriz = false;
    ownerAC.animSpeed = 0.1;

    // Helper highlight function for the formatter
    var highlightMatch = function (full, snippet, matchindex) {
            return full.substring(0, matchindex)
            + "<span class='match'>"
            + full.substr(matchindex, snippet.length)
            + "</span>" + full.substring(matchindex + snippet.length);
        };

    // Custom formatter to highlight the matching letters
    var custom_formatter = function (oResultData, sQuery, sResultMatch) {
            var query = sQuery.toLowerCase();
            var _gravatar = function(res, em, group){
                if (group !== undefined){
                    em = '/images/icons/group.png'
                }
                tmpl = '<div class="ac-container-wrap"><img class="perm-gravatar-ac" src="{0}"/>{1}</div>'
                return tmpl.format(em,res)
            }
            // group
            if (oResultData.grname != undefined) {
                var grname = oResultData.grname;
                var grmembers = oResultData.grmembers;
                var grnameMatchIndex = grname.toLowerCase().indexOf(query);
                var grprefix = "{0}: ".format(_TM['Group']);
                var grsuffix = " (" + grmembers + "  )";
                var grsuffix = " ({0}  {1})".format(grmembers, _TM['members']);

                if (grnameMatchIndex > -1) {
                    return _gravatar(grprefix + highlightMatch(grname, query, grnameMatchIndex) + grsuffix,null,true);
                }
                return _gravatar(grprefix + oResultData.grname + grsuffix, null,true);
            // Users
            } else if (oResultData.nname != undefined) {
                var fname = oResultData.fname || "";
                var lname = oResultData.lname || "";
                var nname = oResultData.nname;

                // Guard against null value
                var fnameMatchIndex = fname.toLowerCase().indexOf(query),
                    lnameMatchIndex = lname.toLowerCase().indexOf(query),
                    nnameMatchIndex = nname.toLowerCase().indexOf(query),
                    displayfname, displaylname, displaynname;

                if (fnameMatchIndex > -1) {
                    displayfname = highlightMatch(fname, query, fnameMatchIndex);
                } else {
                    displayfname = fname;
                }

                if (lnameMatchIndex > -1) {
                    displaylname = highlightMatch(lname, query, lnameMatchIndex);
                } else {
                    displaylname = lname;
                }

                if (nnameMatchIndex > -1) {
                    displaynname = "(" + highlightMatch(nname, query, nnameMatchIndex) + ")";
                } else {
                    displaynname = nname ? "(" + nname + ")" : "";
                }

                return _gravatar(displayfname + " " + displaylname + " " + displaynname, oResultData.gravatar_lnk);
            } else {
                return '';
            }
        };
    membersAC.formatResult = custom_formatter;
    ownerAC.formatResult = custom_formatter;

    var myHandler = function (sType, aArgs) {
            var nextId = divid.split('perm_new_member_name_')[1];
            var myAC = aArgs[0]; // reference back to the AC instance
            var elLI = aArgs[1]; // reference to the selected LI element
            var oData = aArgs[2]; // object literal of selected item's result data
            //fill the autocomplete with value
            if (oData.nname != undefined) {
                //users
                myAC.getInputEl().value = oData.nname;
                $('#perm_new_member_type_'+nextId).val('user');
            } else {
                //groups
                myAC.getInputEl().value = oData.grname;
                $('#perm_new_member_type_'+nextId).val('users_group');
            }
        };

    membersAC.itemSelectEvent.subscribe(myHandler);
    if(ownerAC.itemSelectEvent){
        ownerAC.itemSelectEvent.subscribe(myHandler);
    }

    return {
        memberDS: memberDS,
        ownerDS: ownerDS,
        membersAC: membersAC,
        ownerAC: ownerAC,
    };
}

var MentionsAutoComplete = function (divid, cont, users_list, groups_list) {
    var myUsers = users_list;
    var myGroups = groups_list;

    // Define a custom search function for the DataSource of users
    var matchUsers = function (sQuery) {
            var org_sQuery = sQuery;
            if(this.mentionQuery == null){
                return []
            }
            sQuery = this.mentionQuery;
            // Case insensitive matching
            var query = sQuery.toLowerCase();
            var i = 0;
            var l = myUsers.length;
            var matches = [];

            // Match against each name of each contact
            for (; i < l; i++) {
                contact = myUsers[i];
                if (((contact.fname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.lname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.nname) && ((contact.nname).toLowerCase().indexOf(query) > -1))) {
                    matches[matches.length] = contact;
                }
            }
            return matches
        };

    //match all
    var matchAll = function (sQuery) {
            u = matchUsers(sQuery);
            return u
        };

    // DataScheme for owner
    var ownerDS = new YAHOO.util.FunctionDataSource(matchUsers);

    ownerDS.responseSchema = {
        fields: ["id", "fname", "lname", "nname", "gravatar_lnk"]
    };

    // Instantiate AutoComplete for mentions
    var ownerAC = new YAHOO.widget.AutoComplete(divid, cont, ownerDS);
    ownerAC.useShadow = false;
    ownerAC.resultTypeList = false;
    ownerAC.suppressInputUpdate = true;
    ownerAC.animVert = false;
    ownerAC.animHoriz = false;
    ownerAC.animSpeed = 0.1;

    // Helper highlight function for the formatter
    var highlightMatch = function (full, snippet, matchindex) {
            return full.substring(0, matchindex)
            + "<span class='match'>"
            + full.substr(matchindex, snippet.length)
            + "</span>" + full.substring(matchindex + snippet.length);
        };

    // Custom formatter to highlight the matching letters
    ownerAC.formatResult = function (oResultData, sQuery, sResultMatch) {
            var org_sQuery = sQuery;
            if(this.dataSource.mentionQuery != null){
                sQuery = this.dataSource.mentionQuery;
            }

            var query = sQuery.toLowerCase();
            var _gravatar = function(res, em, group){
                if (group !== undefined){
                    em = '/images/icons/group.png'
                }
                tmpl = '<div class="ac-container-wrap"><img class="perm-gravatar-ac" src="{0}"/>{1}</div>'
                return tmpl.format(em,res)
            }
            if (oResultData.nname != undefined) {
                var fname = oResultData.fname || "";
                var lname = oResultData.lname || "";
                var nname = oResultData.nname;

                // Guard against null value
                var fnameMatchIndex = fname.toLowerCase().indexOf(query),
                    lnameMatchIndex = lname.toLowerCase().indexOf(query),
                    nnameMatchIndex = nname.toLowerCase().indexOf(query),
                    displayfname, displaylname, displaynname;

                if (fnameMatchIndex > -1) {
                    displayfname = highlightMatch(fname, query, fnameMatchIndex);
                } else {
                    displayfname = fname;
                }

                if (lnameMatchIndex > -1) {
                    displaylname = highlightMatch(lname, query, lnameMatchIndex);
                } else {
                    displaylname = lname;
                }

                if (nnameMatchIndex > -1) {
                    displaynname = "(" + highlightMatch(nname, query, nnameMatchIndex) + ")";
                } else {
                    displaynname = nname ? "(" + nname + ")" : "";
                }

                return _gravatar(displayfname + " " + displaylname + " " + displaynname, oResultData.gravatar_lnk);
            } else {
                return '';
            }
        };

    if(ownerAC.itemSelectEvent){
        ownerAC.itemSelectEvent.subscribe(function (sType, aArgs) {

            var myAC = aArgs[0]; // reference back to the AC instance
            var elLI = aArgs[1]; // reference to the selected LI element
            var oData = aArgs[2]; // object literal of selected item's result data
            //fill the autocomplete with value
            if (oData.nname != undefined) {
                //users
                //Replace the mention name with replaced
                var re = new RegExp();
                var org = myAC.getInputEl().value;
                var chunks = myAC.dataSource.chunks
                // replace middle chunk(the search term) with actuall  match
                chunks[1] = chunks[1].replace('@'+myAC.dataSource.mentionQuery,
                                              '@'+oData.nname+' ');
                myAC.getInputEl().value = chunks.join('')
                myAC.getInputEl().focus(); // Y U NO WORK !?
            } else {
                //groups
                myAC.getInputEl().value = oData.grname;
                $('#perm_new_member_type').val('users_group');
            }
        });
    }

    // in this keybuffer we will gather current value of search !
    // since we need to get this just when someone does `@` then we do the
    // search
    ownerAC.dataSource.chunks = [];
    ownerAC.dataSource.mentionQuery = null;

    ownerAC.get_mention = function(msg, max_pos) {
        var org = msg;
        var re = new RegExp('(?:^@|\s@)([a-zA-Z0-9]{1}[a-zA-Z0-9\-\_\.]+)$')
        var chunks  = [];

        // cut first chunk until curret pos
        var to_max = msg.substr(0, max_pos);
        var at_pos = Math.max(0,to_max.lastIndexOf('@')-1);
        var msg2 = to_max.substr(at_pos);

        chunks.push(org.substr(0,at_pos))// prefix chunk
        chunks.push(msg2)                // search chunk
        chunks.push(org.substr(max_pos)) // postfix chunk

        // clean up msg2 for filtering and regex match
        var msg2 = msg2.lstrip(' ').lstrip('\n');

        if(re.test(msg2)){
            var unam = re.exec(msg2)[1];
            return [unam, chunks];
        }
        return [null, null];
    };

    if (ownerAC.textboxKeyUpEvent){
        ownerAC.textboxKeyUpEvent.subscribe(function(type, args){

            var ac_obj = args[0];
            var currentMessage = args[1];
            var currentCaretPosition = args[0]._elTextbox.selectionStart;

            var unam = ownerAC.get_mention(currentMessage, currentCaretPosition);
            var curr_search = null;
            if(unam[0]){
                curr_search = unam[0];
            }

            ownerAC.dataSource.chunks = unam[1];
            ownerAC.dataSource.mentionQuery = curr_search;

        })
    }
    return {
        ownerDS: ownerDS,
        ownerAC: ownerAC,
    };
}

var addReviewMember = function(id,fname,lname,nname,gravatar_link){
    var tmpl = '<li id="reviewer_{2}">'+
    '<div class="reviewers_member">'+
      '<div class="gravatar"><img alt="gravatar" src="{0}"/> </div>'+
      '<div style="float:left">{1}</div>'+
      '<input type="hidden" value="{2}" name="review_members" />'+
      '<span class="delete_icon action_button" onclick="removeReviewMember({2})"></span>'+
    '</div>'+
    '</li>' ;
    var displayname = "{0} {1} ({2})".format(fname,lname,nname);
    var element = tmpl.format(gravatar_link,displayname,id);
    // check if we don't have this ID already in
    var ids = [];
    $('#review_members').find('li').each(function() {
            ids.push(this.id);
        });
    if(ids.indexOf('reviewer_'+id) == -1){
        //only add if it's not there
        $('#review_members').append(element);
    }
}

var removeReviewMember = function(reviewer_id, repo_name, pull_request_id){
    $('#reviewer_{0}'.format(reviewer_id)).remove();
}

/* handle "Save Changes" of addReviewMember and removeReviewMember on PR */
var updateReviewers = function(reviewers_ids, repo_name, pull_request_id){
    if (reviewers_ids === undefined){
        var reviewers_ids = [];
        $('#review_members').find('input').each(function(){
                reviewers_ids.push(this.value);
            });
    }
    var url = pyroutes.url('pullrequest_update', {"repo_name":repo_name,
                                                  "pull_request_id": pull_request_id});
    var postData = {'_method':'put',
                    'reviewers_ids': reviewers_ids};
    var success = function(o){
        window.location.reload();
    }
    ajaxPOST(url,postData,success);
}

/* activate auto completion of users and groups ... but only used for users as PR reviewers */
var PullRequestAutoComplete = function (divid, cont, users_list, groups_list) {
    var myUsers = users_list;
    var myGroups = groups_list;

    // Define a custom search function for the DataSource of users
    var matchUsers = function (sQuery) {
            // Case insensitive matching
            var query = sQuery.toLowerCase();
            var i = 0;
            var l = myUsers.length;
            var matches = [];

            // Match against each name of each contact
            for (; i < l; i++) {
                contact = myUsers[i];
                if (((contact.fname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.lname+"").toLowerCase().indexOf(query) > -1) ||
                     ((contact.nname) && ((contact.nname).toLowerCase().indexOf(query) > -1))) {
                    matches[matches.length] = contact;
                }
            }
            return matches;
        };

    // Define a custom search function for the DataSource of userGroups
    var matchGroups = function (sQuery) {
            // Case insensitive matching
            var query = sQuery.toLowerCase();
            var i = 0;
            var l = myGroups.length;
            var matches = [];

            // Match against each name of each contact
            for (; i < l; i++) {
                matched_group = myGroups[i];
                if (matched_group.grname.toLowerCase().indexOf(query) > -1) {
                    matches[matches.length] = matched_group;
                }
            }
            return matches;
        };

    //match all
    var matchAll = function (sQuery) {
            u = matchUsers(sQuery);
            return u
        };

    // DataScheme for owner
    var ownerDS = new YAHOO.util.FunctionDataSource(matchUsers);

    ownerDS.responseSchema = {
        fields: ["id", "fname", "lname", "nname", "gravatar_lnk"]
    };

    // Instantiate AutoComplete for mentions
    var reviewerAC = new YAHOO.widget.AutoComplete(divid, cont, ownerDS);
    reviewerAC.useShadow = false;
    reviewerAC.resultTypeList = false;
    reviewerAC.suppressInputUpdate = true;
    reviewerAC.animVert = false;
    reviewerAC.animHoriz = false;
    reviewerAC.animSpeed = 0.1;

    // Helper highlight function for the formatter
    var highlightMatch = function (full, snippet, matchindex) {
            return full.substring(0, matchindex)
            + "<span class='match'>"
            + full.substr(matchindex, snippet.length)
            + "</span>" + full.substring(matchindex + snippet.length);
        };

    // Custom formatter to highlight the matching letters
    reviewerAC.formatResult = function (oResultData, sQuery, sResultMatch) {
            var org_sQuery = sQuery;
            if(this.dataSource.mentionQuery != null){
                sQuery = this.dataSource.mentionQuery;
            }

            var query = sQuery.toLowerCase();
            var _gravatar = function(res, em, group){
                if (group !== undefined){
                    em = '/images/icons/group.png'
                }
                tmpl = '<div class="ac-container-wrap"><img class="perm-gravatar-ac" src="{0}"/>{1}</div>'
                return tmpl.format(em,res)
            }
            if (oResultData.nname != undefined) {
                var fname = oResultData.fname || "";
                var lname = oResultData.lname || "";
                var nname = oResultData.nname;

                // Guard against null value
                var fnameMatchIndex = fname.toLowerCase().indexOf(query),
                    lnameMatchIndex = lname.toLowerCase().indexOf(query),
                    nnameMatchIndex = nname.toLowerCase().indexOf(query),
                    displayfname, displaylname, displaynname;

                if (fnameMatchIndex > -1) {
                    displayfname = highlightMatch(fname, query, fnameMatchIndex);
                } else {
                    displayfname = fname;
                }

                if (lnameMatchIndex > -1) {
                    displaylname = highlightMatch(lname, query, lnameMatchIndex);
                } else {
                    displaylname = lname;
                }

                if (nnameMatchIndex > -1) {
                    displaynname = "(" + highlightMatch(nname, query, nnameMatchIndex) + ")";
                } else {
                    displaynname = nname ? "(" + nname + ")" : "";
                }

                return _gravatar(displayfname + " " + displaylname + " " + displaynname, oResultData.gravatar_lnk);
            } else {
                return '';
            }
        };

    //members cache to catch duplicates
    reviewerAC.dataSource.cache = [];
    // hack into select event
    if(reviewerAC.itemSelectEvent){
        reviewerAC.itemSelectEvent.subscribe(function (sType, aArgs) {

            var myAC = aArgs[0]; // reference back to the AC instance
            var elLI = aArgs[1]; // reference to the selected LI element
            var oData = aArgs[2]; // object literal of selected item's result data

            //fill the autocomplete with value
            if (oData.nname != undefined) {
                addReviewMember(oData.id, oData.fname, oData.lname, oData.nname,
                                oData.gravatar_lnk);
                myAC.dataSource.cache.push(oData.id);
                $('#user').val('');
            }
        });
    }
}

/**
 * Activate .quick_repo_menu
 */
var quick_repo_menu = function(){
    $(".quick_repo_menu").mouseenter(function(e) {
            var $menu = $(e.currentTarget).children().first().children().first();
            if($menu.hasClass('hidden')){
                $menu.removeClass('hidden').addClass('active');
                $(e.currentTarget).removeClass('hidden').addClass('active');
            }
        })
    $(".quick_repo_menu").mouseleave(function(e) {
            var $menu = $(e.currentTarget).children().first().children().first();
            if($menu.hasClass('active')){
                $menu.removeClass('active').addClass('hidden');
                $(e.currentTarget).removeClass('active').addClass('hidden');
            }
        })
};


/**
 * TABLE SORTING
 */

// returns a node from given html;
var fromHTML = function(html){
    var _html = document.createElement('element');
    _html.innerHTML = html;
    return _html;
}

var get_rev = function(node){
    var n = node.firstElementChild.firstElementChild;

    if (n===null){
        return -1
    }
    else{
        out = n.firstElementChild.innerHTML.split(':')[0].replace('r','');
        return parseInt(out);
    }
}

var get_date = function(node){
    return $(node.firstElementChild).attr('date');
}

var revisionSort = function(a, b, desc, field) {
    var a_ = get_rev(fromHTML(a.getData(field)));
    var b_ = get_rev(fromHTML(b.getData(field)));

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var ageSort = function(a, b, desc, field) {
    // data is like: <span class="tooltip" date="2014-06-04 18:18:55.325474" title="Wed, 04 Jun 2014 18:18:55">1 day and 23 hours ago</span>
    var a_ = $(a.getData(field)).attr('date');
    var b_ = $(b.getData(field)).attr('date');

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var lastLoginSort = function(a, b, desc, field) {
    var a_ = a.getData('last_login_raw') || 0;
    var b_ = b.getData('last_login_raw') || 0;

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var nameSort = function(a, b, desc, field) {
    var a_ = a.getData('raw_name') || 0;
    var b_ = b.getData('raw_name') || 0;

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var dateSort = function(a, b, desc, field) {
    var a_ = get_date(fromHTML(a.getData(field)));
    var b_ = get_date(fromHTML(b.getData(field)));

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var addPermAction = function(_html, users_list, groups_list){
    var $last_node = $('.last_new_member').last(); // empty tr between last and add
    var next_id = $('.new_members').length;
    $last_node.before($('<tr class="new_members">').append(_html.format(next_id)));
    _MembersAutoComplete("perm_new_member_name_"+next_id,
            "perm_container_"+next_id, users_list, groups_list);
}

function ajaxActionRevokePermission(url, obj_id, obj_type, field_id, extra_data) {
    var callback = {
        success: function (o) {
            $('#' + field_id).remove();
        },
        failure: function (o) {
            alert(_TM['Failed to remoke permission'] + ": " + o.status);
        },
    };
    query_params = {
        '_method': 'delete'
    }
    // put extra data into POST
    if (extra_data !== undefined && (typeof extra_data === 'object')){
        for(k in extra_data){
            query_params[k] = extra_data[k];
        }
    }

    if (obj_type=='user'){
        query_params['user_id'] = obj_id;
        query_params['obj_type'] = 'user';
    }
    else if (obj_type=='user_group'){
        query_params['user_group_id'] = obj_id;
        query_params['obj_type'] = 'user_group';
    }

    var request = YAHOO.util.Connect.asyncRequest('POST', url, callback,
            _toQueryString(query_params));
};

/* Multi selectors */

var MultiSelectWidget = function(selected_id, available_id, form_id){
    var $availableselect = $('#' + available_id);
    var $selectedselect = $('#' + selected_id);

    //fill available only with those not in selected
    var $selectedoptions = $selectedselect.children('option');
    $availableselect.children('option').filter(function(i, e){
            for(var j = 0, node; node = $selectedoptions[j]; j++){
                if(node.value == e.value){
                    return true;
                }
            }
            return false;
        }).remove();

    $('#add_element').click(function(e){
            $selectedselect.append($availableselect.children('option:selected'));
        });
    $('#remove_element').click(function(e){
            $availableselect.append($selectedselect.children('option:selected'));
        });
    $('#add_all_elements').click(function(e){
            $selectedselect.append($availableselect.children('option'));
        });
    $('#remove_all_elements').click(function(e){
            $availableselect.append($selectedselect.children('option'));
        });

    $('#'+form_id).submit(function(){
            $selectedselect.children('option').each(function(i, e){
                e.selected = 'selected';
            });
        });
}

// custom paginator
var YUI_paginator = function(links_per_page, containers){

    (function () {

        var Paginator = YAHOO.widget.Paginator,
            l         = YAHOO.lang,
            setId     = YAHOO.util.Dom.generateId;

        Paginator.ui.MyFirstPageLink = function (p) {
            this.paginator = p;

            p.subscribe('recordOffsetChange',this.update,this,true);
            p.subscribe('rowsPerPageChange',this.update,this,true);
            p.subscribe('totalRecordsChange',this.update,this,true);
            p.subscribe('destroy',this.destroy,this,true);

            // TODO: make this work
            p.subscribe('firstPageLinkLabelChange',this.update,this,true);
            p.subscribe('firstPageLinkClassChange',this.update,this,true);
        };

        Paginator.ui.MyFirstPageLink.init = function (p) {
            p.setAttributeConfig('firstPageLinkLabel', {
                value : 1,
                validator : l.isString
            });
            p.setAttributeConfig('firstPageLinkClass', {
                value : 'yui-pg-first',
                validator : l.isString
            });
            p.setAttributeConfig('firstPageLinkTitle', {
                value : 'First Page',
                validator : l.isString
            });
        };

        // Instance members and methods
        Paginator.ui.MyFirstPageLink.prototype = {
            current   : null,
            leftmost_page: null,
            rightmost_page: null,
            link      : null,
            span      : null,
            dotdot    : null,
            getPos    : function(cur_page, max_page, items){
                var edge = parseInt(items / 2) + 1;
                if (cur_page <= edge){
                    var radius = Math.max(parseInt(items / 2), items - cur_page);
                }
                else if ((max_page - cur_page) < edge) {
                    var radius = (items - 1) - (max_page - cur_page);
                }
                else{
                    var radius = parseInt(items / 2);
                }

                var left = Math.max(1, (cur_page - (radius)))
                var right = Math.min(max_page, cur_page + (radius))
                return [left, cur_page, right]
            },
            render : function (id_base) {
                var p      = this.paginator,
                    c      = p.get('firstPageLinkClass'),
                    label  = p.get('firstPageLinkLabel'),
                    title  = p.get('firstPageLinkTitle');

                this.link     = document.createElement('a');
                this.span     = document.createElement('span');
                $(this.span).hide();

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                setId(this.link, id_base + '-first-link');
                this.link.href      = '#';
                this.link.className = c;
                this.link.innerHTML = label;
                this.link.title     = title;
                YUE.on(this.link,'click',this.onClick,this,true);

                setId(this.span, id_base + '-first-span');
                this.span.className = c;
                this.span.innerHTML = label;

                this.current = p.getCurrentPage() > 1 ? this.link : this.span;
                return this.current;
            },
            update : function (e) {
                var p      = this.paginator;
                var _pos   = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                if (e && e.prevValue === e.newValue) {
                    return;
                }

                var par = this.current ? this.current.parentNode : null;
                if (this.leftmost_page > 1) {
                    if (par && this.current === this.span) {
                        par.replaceChild(this.link,this.current);
                        this.current = this.link;
                    }
                } else {
                    if (par && this.current === this.link) {
                        par.replaceChild(this.span,this.current);
                        this.current = this.span;
                    }
                }
            },
            destroy : function () {
                YUE.purgeElement(this.link);
                this.current.parentNode.removeChild(this.current);
                this.link = this.span = null;
            },
            onClick : function (e) {
                YUE.stopEvent(e);
                this.paginator.setPage(1);
            }
        };

        })();

    (function () {

        var Paginator = YAHOO.widget.Paginator,
            l         = YAHOO.lang,
            setId     = YAHOO.util.Dom.generateId;

        Paginator.ui.MyLastPageLink = function (p) {
            this.paginator = p;

            p.subscribe('recordOffsetChange',this.update,this,true);
            p.subscribe('rowsPerPageChange',this.update,this,true);
            p.subscribe('totalRecordsChange',this.update,this,true);
            p.subscribe('destroy',this.destroy,this,true);

            // TODO: make this work
            p.subscribe('lastPageLinkLabelChange',this.update,this,true);
            p.subscribe('lastPageLinkClassChange', this.update,this,true);
        };

        Paginator.ui.MyLastPageLink.init = function (p) {
            p.setAttributeConfig('lastPageLinkLabel', {
                value : -1,
                validator : l.isString
            });
            p.setAttributeConfig('lastPageLinkClass', {
                value : 'yui-pg-last',
                validator : l.isString
            });
            p.setAttributeConfig('lastPageLinkTitle', {
                value : 'Last Page',
                validator : l.isString
            });

        };

        Paginator.ui.MyLastPageLink.prototype = {

            current   : null,
            leftmost_page: null,
            rightmost_page: null,
            link      : null,
            span      : null,
            dotdot    : null,
            na        : null,
            getPos    : function(cur_page, max_page, items){
                var edge = parseInt(items / 2) + 1;
                if (cur_page <= edge){
                    var radius = Math.max(parseInt(items / 2), items - cur_page);
                }
                else if ((max_page - cur_page) < edge) {
                    var radius = (items - 1) - (max_page - cur_page);
                }
                else{
                    var radius = parseInt(items / 2);
                }

                var left = Math.max(1, (cur_page - (radius)))
                var right = Math.min(max_page, cur_page + (radius))
                return [left, cur_page, right]
            },
            render : function (id_base) {
                var p      = this.paginator,
                    c      = p.get('lastPageLinkClass'),
                    label  = p.get('lastPageLinkLabel'),
                    last   = p.getTotalPages(),
                    title  = p.get('lastPageLinkTitle');

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                this.link = document.createElement('a');
                this.span = document.createElement('span');
                $(this.span).hide();

                this.na   = this.span.cloneNode(false);

                setId(this.link, id_base + '-last-link');
                this.link.href      = '#';
                this.link.className = c;
                this.link.innerHTML = label;
                this.link.title     = title;
                YUE.on(this.link,'click',this.onClick,this,true);

                setId(this.span, id_base + '-last-span');
                this.span.className = c;
                this.span.innerHTML = label;

                setId(this.na, id_base + '-last-na');

                if (this.rightmost_page < p.getTotalPages()){
                    this.current = this.link;
                }
                else{
                    this.current = this.span;
                }

                this.current.innerHTML = p.getTotalPages();
                return this.current;
            },

            update : function (e) {
                var p      = this.paginator;

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                if (e && e.prevValue === e.newValue) {
                    return;
                }

                var par   = this.current ? this.current.parentNode : null,
                    after = this.link;
                if (par) {

                    // only show the last page if the rightmost one is
                    // lower, so we don't have doubled entries at the end
                    if (!(this.rightmost_page < p.getTotalPages())){
                        after = this.span
                    }

                    if (this.current !== after) {
                        par.replaceChild(after,this.current);
                        this.current = after;
                    }
                }
                this.current.innerHTML = this.paginator.getTotalPages();

            },
            destroy : function () {
                YUE.purgeElement(this.link);
                this.current.parentNode.removeChild(this.current);
                this.link = this.span = null;
            },
            onClick : function (e) {
                YUE.stopEvent(e);
                this.paginator.setPage(this.paginator.getTotalPages());
            }
        };

        })();

    var pagi = new YAHOO.widget.Paginator({
        rowsPerPage: links_per_page,
        alwaysVisible: false,
        template : "{PreviousPageLink} {MyFirstPageLink} {PageLinks} {MyLastPageLink} {NextPageLink}",
        pageLinks: 5,
        containerClass: 'pagination-wh',
        currentPageClass: 'pager_curpage',
        pageLinkClass: 'pager_link',
        nextPageLinkLabel: '&gt;',
        previousPageLinkLabel: '&lt;',
        containers:containers
    })

    return pagi
}


// global hooks after DOM is loaded

$(document).ready(function(){
    $('.diff-collapse-button').click(function(e) {
        var $button = $(e.currentTarget);
        var $target = $('#' + $button.attr('target'));
        if($target.hasClass('hidden')){
            $target.removeClass('hidden');
            $button.html("&uarr; {0} &uarr;".format(_TM['Collapse diff']));
        }
        else if(!$target.hasClass('hidden')){
            $target.addClass('hidden');
            $button.html("&darr; {0} &darr;".format(_TM['Expand diff']));
        }
    });
});
