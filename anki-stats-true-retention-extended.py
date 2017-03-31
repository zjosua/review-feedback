# -*- coding: utf-8 -*-

"""
True Retention Add-on for Anki (extended)

Based on True Retention by unknown author
(https://ankiweb.net/shared/info/613684242)

Copyright: (c) 2016 unknown author
           (c) 2017 Glutanimate (https://github.com/Glutanimate)

License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html
"""

### USER CONFIGURATION START ###

MATURE_IVL = 21 # mature card interval in days

### USER CONFIGURATION END ####

import anki.stats

from anki.utils import fmtTimeSpan, ids2str
from anki.lang import _, ngettext


# Types: 0 - new today; 1 - review; 2 - relearn; 3 - (cram?) [before the answer was pressed]
# "Learning" corresponds to New|Relearn. "Review" corresponds to Young|Mature.
# Ease: 1 - flunk button; 2 - second; 3 - third; 4 - fourth (easy) [which button was pressed]
# Intervals: -60 <1m -600 10m etc; otherwise days (>=21 is mature)
def _line_now(self, i, a, b, bold=True):
    colon = _(":")
    if bold:
        i.append(("<tr><td align=right>%s%s</td><td><b>%s</b></td></tr>") % (a,colon,b))
    else:
        i.append(("<tr><td align=right>%s%s</td><td>%s</td></tr>") % (a,colon,b))

def _lineTbl_now(self, i):
    return "<table>" + "".join(i) + "</table>"

def statList(self, lim, span):
    yflunked, ypassed, mflunked, mpassed, learned, relearned = self.col.db.first("""
    select
    sum(case when lastIvl < %(i)d and ease = 1 and type == 1 then 1 else 0 end), /* flunked young */
    sum(case when lastIvl < %(i)d and ease > 1 and type == 1 then 1 else 0 end), /* passed young */
    sum(case when lastIvl >= %(i)d and ease = 1 and type == 1 then 1 else 0 end), /* flunked mature */
    sum(case when lastIvl >= %(i)d and ease > 1 and type == 1 then 1 else 0 end), /* passed mature */
    sum(case when ivl > 0 and type == 0 then 1 else 0 end), /* learned */
    sum(case when ivl > 0 and type == 2 then 1 else 0 end) /* relearned */
    from revlog where id > ? """ % dict(i=MATURE_IVL) +lim, span)
    yflunked = yflunked or 0
    mflunked = mflunked or 0
    ypassed = ypassed or 0
    mpassed = mpassed or 0
    learned = learned or 0
    relearned = relearned or 0
    try:
        ytemp = "%0.1f%%" %(ypassed/float(ypassed+yflunked)*100)
    except ZeroDivisionError:
        ytemp = "N/A"

    try:
        mtemp = "%0.1f%%" %(mpassed/float(mpassed+mflunked)*100)
    except ZeroDivisionError:
        mtemp = "N/A"

    try:
        ttemp = "%0.1f%%" %((ypassed+mpassed)/float(ypassed+mpassed+yflunked+mflunked)*100)
    except ZeroDivisionError:
        ttemp = "N/A"
    
    i = []
    i.append("""<style>tr.trsct{height: 2.5em; text-align: center; font-style: italic;}</style>""")
    i.append("<tr class='trsct'><td colspan='2'>Young cards</center></td></tr>")
    _line_now(self, i, "True retention", ytemp)
    _line_now(self, i, "Passed reviews", ypassed)
    _line_now(self, i, "Flunked reviews", yflunked)
    i.append("<tr class='trsct'><td colspan='2'>Mature cards (ivl≥%d)</center></td></tr>" % MATURE_IVL)
    _line_now(self, i, "True retention", mtemp)
    _line_now(self, i, "Passed reviews", mpassed)
    _line_now(self, i, "Flunked reviews", mflunked)
    i.append("<tr class='trsct'><td colspan='2'>Total</center></td></tr>")
    _line_now(self, i, "True retention", ttemp)
    _line_now(self, i, "Passed reviews", ypassed+mpassed)
    _line_now(self, i, "Flunked reviews", yflunked+yflunked)
    _line_now(self, i, "New cards learned", learned)
    _line_now(self, i, "Cards relearned", relearned)
    return _lineTbl_now(self, i)

def todayStats_new(self):
    lim = self._revlogLimit()
    if lim:
        lim = " and " + lim
    
    pastDay = statList(self, lim, (self.col.sched.dayCutoff-86400)*1000)
    pastWeek = statList(self, lim, (self.col.sched.dayCutoff-86400*7)*1000)
    
    if self.type == 0:
        period = 31; name = "<strong>Past month:</strong>"
    elif self.type == 1:
        period = 365; name = "<strong>Past year:</strong>"
    elif self.type == 2:
        period = float('inf'); name = "<strong>All time:</strong>"
    
    pastPeriod = statList(self, lim, (self.col.sched.dayCutoff-86400*period)*1000)
    
    return todayStats_old(self) + "<br><br><table style='text-align: center'><tr><td style='padding: 5px'>" \
        + "<span><strong>Past day:</strong></span>" + pastDay + "</td><td style='padding: 5px'>" \
        + "<span><strong>Past week:</strong></span>" + pastWeek + "</td><td style='padding: 5px'>" \
        + "<span>" + name + "</span>" + pastPeriod + "</td></tr></table>"

def todayStats_old(self):
    """We need to overwrite the entire method to change the mature ivl"""
    b = self._title(_("Today"))
    # studied today
    lim = self._revlogLimit()
    if lim:
        lim = " and " + lim
    cards, thetime, failed, lrn, rev, relrn, filt = self.col.db.first("""
select count(), sum(time)/1000,
sum(case when ease = 1 then 1 else 0 end), /* failed */
sum(case when type = 0 then 1 else 0 end), /* learning */
sum(case when type = 1 then 1 else 0 end), /* review */
sum(case when type = 2 then 1 else 0 end), /* relearn */
sum(case when type = 3 then 1 else 0 end) /* filter */
from revlog where id > ? """+lim, (self.col.sched.dayCutoff-86400)*1000)
    cards = cards or 0
    thetime = thetime or 0
    failed = failed or 0
    lrn = lrn or 0
    rev = rev or 0
    relrn = relrn or 0
    filt = filt or 0
    # studied
    def bold(s):
        return "<b>"+unicode(s)+"</b>"
    msgp1 = ngettext("<!--studied-->%d card", "<!--studied-->%d cards", cards) % cards
    b += _("Studied %(a)s in %(b)s today.") % dict(
        a=bold(msgp1), b=bold(fmtTimeSpan(thetime, unit=1)))
    # again/pass count
    b += "<br>" + _("Again count: %s") % bold(failed)
    if cards:
        b += " " + _("(%s correct)") % bold(
            "%0.1f%%" %((1-failed/float(cards))*100))
    # type breakdown
    b += "<br>"
    b += (_("Learn: %(a)s, Review: %(b)s, Relearn: %(c)s, Filtered: %(d)s")
          % dict(a=bold(lrn), b=bold(rev), c=bold(relrn), d=bold(filt)))
    # mature today
    mcnt, msum = self.col.db.first("""
select count(), sum(case when ease = 1 then 0 else 1 end) from revlog
where lastIvl >= %d and id > ?""" % MATURE_IVL +lim, (self.col.sched.dayCutoff-86400)*1000)
    b += "<br>"
    if mcnt:
        b += _("Correct answers on mature cards: %(a)d/%(b)d (%(c).1f%%)") % dict(
            a=msum, b=mcnt, c=(msum / float(mcnt) * 100))
    else:
        b += _("No mature cards were studied today.")
    return b

anki.stats.CollectionStats.todayStats = todayStats_new
