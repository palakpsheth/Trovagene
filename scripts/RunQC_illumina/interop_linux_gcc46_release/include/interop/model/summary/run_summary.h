/** Summary statistics over entire run
 *
 *  @file
 *  @date  3/5/16
 *  @version 1.0
 *  @copyright GNU Public License.
 */
#pragma once

#include <vector>
#include "interop/util/exception.h"
#include "interop/util/assert.h"
#include "interop/model/summary/read_summary.h"
#include "interop/model/model_exceptions.h"
#include "interop/io/stream_exceptions.h"

namespace illumina { namespace interop { namespace model { namespace summary
{
    /**  Summary statistics over entire run
     *
     */
    class run_summary
    {
    public:
        /** Read summary vector type */
        typedef std::vector<read_summary> read_summary_vector_t;
    public:
        /** Reference to read_summary */
        typedef read_summary_vector_t::reference reference;
        /** Constant reference to read_summary */
        typedef read_summary_vector_t::const_reference const_reference;
        /** Random access iterator to vector of read_summary */
        typedef read_summary_vector_t::iterator iterator;
        /** Constant random access iterator to vector of read_summary */
        typedef read_summary_vector_t::const_iterator const_iterator;
        /** Unsigned integral type (usually size_t) */
        typedef read_summary_vector_t::size_type size_type;
    public:
        /** Constructor
         */
        run_summary() : m_lane_count(0), m_read_count(0)
        {
        }

        /** Constructor
         *
         * @param beg iterator to start of read collection
         * @param end iterator to end of read collection
         * @param lane_count number of lanes on flowcell
         */
        template<typename I>
        run_summary(I beg, I end, const size_t lane_count) : m_lane_count(lane_count),
                                                             m_summary_by_read(beg, end)
        {
            m_read_count = m_summary_by_read.size();
            for (iterator b = m_summary_by_read.begin(), e = m_summary_by_read.end(); b != e; ++b)
            {
                b->resize(lane_count);
                for (size_t lane = 0; lane < lane_count; ++lane)
                    b->at(lane).lane(lane + 1);
            }
        }

        /** Constructor
         *
         * @param reads read info vector
         * @param lane_count number of lanes on flowcell
         */
        run_summary(const std::vector<run::read_info> &reads, const size_t lane_count) : m_lane_count(lane_count),
                                                                                         m_summary_by_read(
                                                                                                 reads.begin(),
                                                                                                 reads.end())
        {
            m_read_count = reads.size();
            for (iterator b = m_summary_by_read.begin(), e = m_summary_by_read.end(); b != e; ++b)
            {
                b->resize(lane_count);
                for (size_t lane = 0; lane < lane_count; ++lane)
                    b->at(lane).lane(lane + 1);
            }
        }

    public:
        /** Initialize the run summary with the number of reads and lanes
         *
         * @param reads vector of reads
         * @param lane_count number of lanes
         */
        void initialize(const std::vector<run::read_info> &reads, const size_t lane_count)
        {
            m_read_count = reads.size();
            m_summary_by_read.clear();
            m_summary_by_read.reserve(reads.size());
            for (size_t read = 0; read < reads.size(); ++read)
                m_summary_by_read.push_back(read_summary(reads[read]));
            m_lane_count = lane_count;
            for (iterator b = m_summary_by_read.begin(), e = m_summary_by_read.end(); b != e; ++b)
            {
                b->resize(lane_count);
                for (size_t lane = 0; lane < lane_count; ++lane)
                    b->at(lane).lane(lane + 1);
            }
        }
        /** Copy reads to destination vector
         *
         * @param dst destination vector
         */
        void copy_reads(std::vector<run::read_info> & dst)
        {
            dst.resize(size());
            for(size_t i=0;i<dst.size();++i) dst[i] = m_summary_by_read[i].read();
        }

    public:
        /** @defgroup run_summary Run Summary
         *
         * Information used in the SAV Summary Tab
         *
         * @ref illumina::interop::model::summary::run_summary "See full class description"
         * @{
         */
        /** Get reference to read_summary at given index
         *
         * @param n index
         * @return reference to read_summary
         */
        reference operator[](const size_type n) throw(model::index_out_of_bounds_exception)
        {
            if (n >= m_summary_by_read.size())
                INTEROP_THROW(index_out_of_bounds_exception, "Read index exceeds read count");
            return m_summary_by_read[n];
        }

        /** Get constant reference to read_summary at given index
         *
         * @param n index
         * @return constant reference to read_summary
         */
        const_reference operator[](const size_type n) const throw(model::index_out_of_bounds_exception)
        {
            if (n >= m_summary_by_read.size())
                INTEROP_THROW(index_out_of_bounds_exception, "Read index exceeds read count");
            return m_summary_by_read[n];
        }

        /** Get reference to read_summary at given index
         *
         * @param n index
         * @return reference to read_summary
         */
        read_summary &at(const size_type n) throw(model::index_out_of_bounds_exception)
        {
            if (n >= m_summary_by_read.size())
                INTEROP_THROW(index_out_of_bounds_exception, "Read index exceeds read count");
            return m_summary_by_read[n];
        }

        /** Get constant reference to read_summary at given index
         *
         * @param n index
         * @return constant reference to read_summary
         */
        const_reference at(const size_type n) const throw(model::index_out_of_bounds_exception)
        {
            if (n >= m_summary_by_read.size())
                INTEROP_THROW(index_out_of_bounds_exception, "Read index exceeds read count");
            return m_summary_by_read[n];
        }

        /** Get number of summaries by read
         *
         * @return number of summaries by read
         */
        size_t size() const
        {
            return m_summary_by_read.size();
        }

        /** Get random access iterator to start of summaries by read
         *
         * @return random access iterator
         */
        iterator begin()
        {
            return m_summary_by_read.begin();
        }

        /** Get random access iterator to end of summaries by read
         *
         * @return random access iterator
         */
        iterator end()
        {
            return m_summary_by_read.end();
        }

        /** Get constant random access iterator to start of summaries by read
         *
         * @return constant random access iterator
         */
        const_iterator begin() const
        {
            return m_summary_by_read.begin();
        }

        /** Get constant random access iterator to end of summaries by read
         *
         * @return constant random access iterator
         */
        const_iterator end() const
        {
            return m_summary_by_read.end();
        }
        /** Clear the contents of the summary
         */
        void clear()
        {
            m_summary_by_read.clear();
            m_lane_count = 0;
            m_read_count = 0;
        }

    public:
        /** Get number of lanes
         *
         * @return number of lanes
         */
        size_t lane_count() const
        {
            return m_lane_count;
        }

        /** Set number of lanes
         *
         * @param lane_count number of lanes
         */
        void lane_count(const size_t lane_count)
        {
            m_lane_count = lane_count;
        }

    public:
        /** Get summary metrics
         *
         * @return summary metrics
         */
        const metric_summary &total_summary() const
        {
            return m_total_summary;
        }

        /** Get summary metrics
         *
         * @return summary metrics
         */
        metric_summary &total_summary()
        {
            return m_total_summary;
        }

        /** Set the summary
         *
         * @param summary metric summary
         */
        void total_summary(const metric_summary &summary)
        {
            m_total_summary = summary;
        }

    public:
        /** Get summary metrics
         *
         * @return summary metrics
         */
        const metric_summary &nonindex_summary() const
        {
            return m_nonindex_summary;
        }

        /** Get summary metrics
         *
         * @return summary metrics
         */
        metric_summary &nonindex_summary()
        {
            return m_nonindex_summary;
        }

        /** Set the summary
         *
         * @param summary metric summary
         */
        void nonindex_summary(const metric_summary &summary)
        {
            m_nonindex_summary = summary;
        }

    public:
        /** Get statistics summarizing the cycle of each RTA state of tiles in the lane
         *
         * @return statistics summarizing the cycle of each RTA state of tiles in the lane
         */
        const cycle_state_summary &cycle_state() const
        {
            return m_cycle_state;
        }

        /** Get statistics summarizing the cycle of each RTA state of tiles in the lane
         *
         * @return statistics summarizing the cycle of each RTA state of tiles in the lane
         */
        cycle_state_summary &cycle_state()
        {
            return m_cycle_state;
        }
        /** @} */

    private:
        /** Resize the run summary with the number of reads and lanes
         *
         * @param read_count number of reads
         * @param lane_count number of lanes
         */
        void resize()
        {
            m_summary_by_read.clear();
            m_summary_by_read.resize(m_read_count);
            for (iterator b = m_summary_by_read.begin(), e = m_summary_by_read.end(); b != e; ++b)
            {
                b->resize(m_lane_count);
            }
        }

        friend std::ostream& operator<<(std::ostream& out, const run_summary& summary);
        friend std::istream& operator>>(std::istream& in, run_summary& summary);

    private:
        size_t m_lane_count;
        size_t m_read_count;
    private:
        metric_summary m_total_summary;
        metric_summary m_nonindex_summary;
        cycle_state_summary m_cycle_state;

    private:
        read_summary_vector_t m_summary_by_read;
        template<class MetricType, int Version>
        friend struct io::generic_layout;
    };

}}}}

